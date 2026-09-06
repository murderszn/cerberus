/* Ink Terminal app — plain ES2018, no bundler, no external deps.
   Reuses window.CerberusScanner (assets/scanner.js) and window.CERBERUS_CHECKS
   (assets/checks.js), plus the agent.html history keys so both pages share
   state: INDEX_KEY='cerberus:index', REPORT_PREFIX='cerberus:report:'.
   Everything rendered here comes from real scan output or real stored
   reports. Demo-only content is always labeled LOCAL. */
(function () {
  'use strict';

  /* ------------------------------------------------------------ utils */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function shortSha(sha) { return sha ? String(sha).slice(0, 7) : '—'; }
  function fmtTime(iso) {
    try { return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
    catch (e) { return iso || ''; }
  }
  function reducedMotion() {
    try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; }
    catch (e) { return false; }
  }

  /* ----------------------------------------------------------- storage */
  var INDEX_KEY = 'cerberus:index';
  var REPORT_PREFIX = 'cerberus:report:';
  var TASKS_KEY = 'cerberus:tasks';
  var DRAFT_KEY = 'cerberus:composer-draft';
  var PAT_KEY = 'cerberus:pat'; // shared with agent.html (sessionStorage)

  function readJSON(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) { return fallback; }
  }
  function writeJSON(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); return true; }
    catch (e) { return false; }
  }
  function readIndex() {
    var idx = readJSON(INDEX_KEY, []);
    if (!Array.isArray(idx)) return [];
    idx.sort(function (a, b) { return (b.cachedAt || 0) - (a.cachedAt || 0); });
    return idx;
  }
  function readReport(entry) {
    if (!entry) return null;
    return readJSON(REPORT_PREFIX + entry.key, null);
  }
  function saveReport(report) {
    var key = report.target.owner + '/' + report.target.repo + '@' + report.target.sha;
    var entry = {
      key: key, owner: report.target.owner, repo: report.target.repo,
      sha: report.target.sha, display: report.target.display,
      score: report.score, grade: report.grade,
      scannedAt: report.scannedAt, cachedAt: Date.now()
    };
    try {
      localStorage.setItem(REPORT_PREFIX + key, JSON.stringify(report));
    } catch (e) {
      // Quota: drop the oldest cached report once, then retry.
      var idx = readJSON(INDEX_KEY, []);
      idx.sort(function (a, b) { return (a.cachedAt || 0) - (b.cachedAt || 0); });
      var victim = idx.shift();
      if (victim) { try { localStorage.removeItem(REPORT_PREFIX + victim.key); } catch (e2) {} }
      try { localStorage.setItem(REPORT_PREFIX + key, JSON.stringify(report)); }
      catch (e3) { return null; }
    }
    var fresh = readJSON(INDEX_KEY, []).filter(function (en) { return en.key !== key; });
    fresh.push(entry);
    fresh.sort(function (a, b) { return (b.cachedAt || 0) - (a.cachedAt || 0); });
    writeJSON(INDEX_KEY, fresh.slice(0, 20));
    return entry;
  }
  function readTasks() {
    var t = readJSON(TASKS_KEY, []);
    return Array.isArray(t) ? t : [];
  }
  function pat() {
    try { return sessionStorage.getItem(PAT_KEY) || ''; }
    catch (e) { return ''; }
  }

  /* -------------------------------------------------------------- net */
  function ghHeaders() {
    var h = { 'Accept': 'application/vnd.github+json' };
    var tok = pat();
    if (tok) h.Authorization = 'Bearer ' + tok;
    return h;
  }
  function probeConnection(done) {
    function set(state, text) { done(state, text); }
    if (!navigator.onLine) { set('offline', 'local / offline'); return; }
    var ctl = new AbortController();
    var t = setTimeout(function () { ctl.abort(); }, 8000);
    fetch('https://api.github.com/rate_limit', { headers: ghHeaders(), signal: ctl.signal })
      .then(function (r) {
        clearTimeout(t);
        if (r.status === 403) { set('limited', 'local / rate-limited'); return; }
        if (!r.ok) throw new Error('http ' + r.status);
        return r.json().then(function (j) {
          var rem = j && j.resources && j.resources.core && j.resources.core.remaining;
          set('connected', 'local / connected' + (rem != null ? ' · ' + rem + ' api' : ''));
        });
      })
      .catch(function () { clearTimeout(t); set('offline', 'local / unreachable'); });
  }
  function ghJSON(url, signal) {
    return fetch(url, { headers: ghHeaders(), signal: signal }).then(function (r) {
      if (r.status === 403) {
        var err = new Error('GitHub API rate limit exceeded. Add a token via /token <pat> (kept in this tab only).');
        err.code = 'RATE_LIMITED'; throw err;
      }
      if (r.status === 404) { var e2 = new Error('Not found (private repo or bad ref?).'); e2.code = 'NOT_FOUND'; throw e2; }
      if (!r.ok) { var e3 = new Error('GitHub API error: http ' + r.status); e3.code = 'HTTP_' + r.status; throw e3; }
      return r.json();
    });
  }

  /* ------------------------------------------------------------- state */
  var state = {
    view: 'task',
    report: null,      // loaded cerberus.report/2 (real scan output)
    entry: null,       // its index entry
    runState: 'idle',  // idle|running|done|failed|stopped
    abort: null,
    tree: null,        // {owner,repo,sha,paths:[...]} file tree cache
    treeKey: '',
    openFile: null
  };

  var work, viewRoot, sessionId, sessionState, envState, envText;
  var composer, composerForm, sendBtn, stopBtn, sideNav, sideFoot;

  function stickBottom() {
    // Follow new output only when the user is already at the bottom.
    var near = work.scrollHeight - work.scrollTop - work.clientHeight < 90;
    if (near) work.scrollTop = work.scrollHeight;
  }

  function setRunState(s, label) {
    state.runState = s;
    sessionState.textContent = label || s;
    sessionState.setAttribute('data-s', s === 'done' ? 'done' : s);
    stopBtn.hidden = (s !== 'running');
    renderSideFoot();
  }

  function setSession(report) {
    if (report) {
      sessionId.textContent = 'SESSION ' + shortSha(report.target.sha) + ' / ' + report.target.display;
    } else {
      sessionId.textContent = 'SESSION — / IDLE';
    }
  }

  function renderSideFoot() {
    var repoEl = $('#sfRepo'), refEl = $('#sfRef'), stEl = $('#sfStatus');
    if (state.report) {
      repoEl.textContent = state.report.target.display;
      refEl.textContent = 'ref ' + (state.report.target.ref || shortSha(state.report.target.sha));
      var fails = 0;
      state.report.agents.forEach(function (a) {
        (a.checks || []).forEach(function (c) { if (c.status === 'fail') fails++; });
      });
      stEl.textContent = state.runState === 'running' ? 'scan running…'
        : fails + ' failing checks · score ' + state.report.score + '/100';
    } else {
      repoEl.textContent = 'no repo loaded';
      refEl.textContent = '—';
      stEl.textContent = state.runState === 'running' ? 'scan running…' : 'workspace idle';
    }
  }

  function setView(name) {
    state.view = name;
    $all('.side-item', sideNav).forEach(function (b) {
      b.setAttribute('aria-current', b.getAttribute('data-view') === name ? 'true' : 'false');
    });
    render();
    work.scrollTop = 0;
  }

  /* ------------------------------------------------------------ render */
  function render() {
    if (state.view === 'files') return renderFiles();
    if (state.view === 'changes') return renderChanges();
    if (state.view === 'history') return renderHistory();
    return renderTask();
  }

  function emptyBox(title, lines, art) {
    var d = document.createElement('div');
    d.className = 'empty';
    var h = '<h2>' + esc(title) + '</h2>';
    var ps = lines.map(function (t) { return '<p>' + esc(t) + '</p>'; }).join('');
    d.innerHTML = (art ? '<img class="stipple" alt="" src="assets/cerberus-stipple.png" />' : '') + h + ps;
    return d;
  }

  function recentTaskButton(entry) {
    var b = document.createElement('button');
    b.type = 'button';
    b.innerHTML = '<span aria-hidden="true">› </span>' + esc(entry.display) +
      '<span class="sub">score ' + esc(String(entry.score)) + '/100 · grade ' + esc(entry.grade) +
      ' · ' + esc(fmtTime(entry.scannedAt)) + '</span>';
    b.addEventListener('click', function () { openEntry(entry); });
    return b;
  }

  function renderTask() {
    viewRoot.innerHTML = '';
    if (state.runState === 'running' || state.feed) { renderFeed(); return; }
    if (state.report) { renderReportSummary(state.report); return; }

    var q = document.createElement('p');
    q.className = 'idle-q';
    q.textContent = 'What are we building?';
    viewRoot.appendChild(q);

    var idx = readIndex();
    if (idx.length) {
      var h = document.createElement('p');
      h.className = 'section-label';
      h.textContent = 'PICK UP WHERE YOU LEFT OFF';
      viewRoot.appendChild(h);
      var ul = document.createElement('ul');
      ul.className = 'recent-list';
      idx.slice(0, 3).forEach(function (entry) {
        var li = document.createElement('li');
        li.appendChild(recentTaskButton(entry));
        ul.appendChild(li);
      });
      viewRoot.appendChild(ul);
    }

    var tasks = readTasks();
    var h2 = document.createElement('p');
    h2.className = 'section-label';
    h2.textContent = tasks.length ? 'SAVED TASKS · LOCAL ONLY' : 'RECENT WORK';
    viewRoot.appendChild(h2);
    if (!idx.length && !tasks.length) {
      viewRoot.appendChild(emptyBox('Nothing scanned yet', [
        'Run /scan owner/repo to audit a public GitHub repository.',
        'Scans run locally in your browser with the same engine as the Cerberus Agent page.'
      ], true));
      return;
    }
    tasks.forEach(function (t) {
      var row = document.createElement('div');
      row.className = 'hist-row';
      row.innerHTML = '<span class="tick" aria-hidden="true">○</span><span>' + esc(t.text) +
        '<span class="tag-local">LOCAL</span></span>' +
        '<span class="meta">' + esc(fmtTime(t.createdAt)) + '</span>';
      viewRoot.appendChild(row);
    });
    if (!tasks.length) {
      idx.slice(0, 5).forEach(function (entry) {
        var ok = entry.grade && entry.grade[0] <= 'B';
        var row = document.createElement('button');
        row.type = 'button';
        row.className = 'hist-row';
        row.innerHTML = '<span class="tick" aria-hidden="true">' + (ok ? '✓' : '✖') + '</span>' +
          '<span>' + esc(entry.display) + '</span>' +
          '<span class="meta">' + esc(String(entry.score)) + '/100 · ' + esc(fmtTime(entry.scannedAt)) + '</span>';
        row.addEventListener('click', function () { openEntry(entry); });
        viewRoot.appendChild(row);
      });
      var note = document.createElement('p');
      note.className = 'hist-sub';
      note.textContent = 'From shared scan history (same list as the Cerberus Agent page).';
      viewRoot.appendChild(note);
    }
  }

  function sevRank(s) { return s === 'critical' ? 0 : s === 'high' ? 1 : s === 'medium' ? 2 : 3; }

  function findingHTML(f, severity) {
    return '<div class="finding sev-' + esc(severity || 'low') + '">' +
      '<div class="floc">' + esc(f.path || '') + (f.line ? ':' + esc(String(f.line)) : '') + '</div>' +
      (f.snippet ? '<code>' + esc(f.snippet) + '</code>' : '') +
      (f.url ? '<div class="floc"><a href="' + esc(f.url) + '" target="_blank" rel="noopener">open on GitHub ↗</a></div>' : '') +
      '</div>';
  }

  function checkDetails(check) {
    var d = document.createElement('details');
    d.className = 'check';
    if (check.status === 'fail') d.open = true;
    var s = document.createElement('summary');
    var stat = check.status === 'fail' ? '✖ FAIL' : check.status === 'pass' ? '✓ pass' : check.status;
    s.innerHTML = '<span class="cid">' + esc(check.id) + '</span><span>' + esc(check.name) + '</span>' +
      '<span class="cstat" data-s="' + esc(check.status) + '">' + esc(stat) + '</span>';
    d.appendChild(s);
    var body = document.createElement('div');
    body.className = 'check-body';
    var html = '<p>' + esc(check.summary || '') + '</p>' +
      '<p><span class="lbl">SEVERITY </span>' + esc(check.severity || '—') +
      (check.cwe ? ' &nbsp; <span class="lbl">CWE </span>' + esc(check.cwe) : '') + '</p>';
    if ((check.findings || []).length) {
      html += check.findings.map(function (f) { return findingHTML(f, check.severity); }).join('');
      if (check.findingsTruncated) html += '<p class="floc">…showing first ' + check.findings.length + ' of ' + esc(String(check.totalFindings)) + '</p>';
    } else if (check.status === 'fail') {
      html += '<p class="floc">Failing condition met; no line-level excerpts retained.</p>';
    }
    if (check.remediation) html += '<p><span class="lbl">FIX </span>' + esc(check.remediation) + '</p>';
    body.innerHTML = html;
    d.appendChild(body);
    return d;
  }

  function renderFeed() {
    viewRoot.innerHTML = '';
    var feed = state.feed;
    var bar = document.createElement('div');
    bar.className = 'progress';
    bar.setAttribute('role', 'progressbar');
    bar.setAttribute('aria-valuemin', '0');
    bar.setAttribute('aria-valuemax', '100');
    bar.setAttribute('aria-valuenow', String(feed.pct));
    bar.innerHTML = '<i style="width:' + feed.pct + '%"></i>';
    viewRoot.appendChild(bar);
    var st = document.createElement('p');
    st.className = 'status-line';
    st.innerHTML = '<strong>' + esc(feed.target.display) + '</strong> · <span class="spinner" aria-hidden="true"></span><span>' + esc(feed.message) + '</span>';
    viewRoot.appendChild(st);
    feed.agentOrder.forEach(function (agentId) {
      var g = feed.groups[agentId];
      var box = document.createElement('div');
      box.className = 'agent-group';
      var head = document.createElement('div');
      head.className = 'agent-head';
      head.innerHTML = '<span class="aname">' + esc(g.name) + '</span><span class="ascore">' + esc(g.done + '/' + g.total + ' checks') + '</span>';
      box.appendChild(head);
      g.checks.forEach(function (c) { box.appendChild(checkDetails(c)); });
      viewRoot.appendChild(box);
    });
    stickBottom();
  }

  function renderReportSummary(report) {
    viewRoot.innerHTML = '';
    var fails = [], passes = 0;
    report.agents.forEach(function (a) {
      (a.checks || []).forEach(function (c) {
        if (c.status === 'fail') fails.push({ agent: a, check: c });
        else passes++;
      });
    });
    fails.sort(function (x, y) { return sevRank(x.check.severity) - sevRank(y.check.severity); });
    var line = document.createElement('p');
    line.className = 'result-line';
    line.innerHTML = '<strong>' + esc(report.target.display) + '</strong> · score ' +
      '<strong>' + esc(String(report.score)) + '/100 (' + esc(report.grade) + ')</strong> · ' +
      '<span class="' + (fails.length ? 'fail' : 'pass') + '">' +
      esc(String(fails.length)) + ' failing, ' + esc(String(passes)) + ' passing</span> · ' +
      '<span style="color:var(--ink-2)">' + esc(fmtTime(report.scannedAt)) + '</span>';
    viewRoot.appendChild(line);
    var h = document.createElement('p');
    h.className = 'section-label';
    h.textContent = fails.length ? 'FINDINGS · EXPAND FOR DETAIL' : 'NO FAILING CHECKS';
    viewRoot.appendChild(h);
    if (!fails.length) {
      viewRoot.appendChild(emptyBox('Clean scan', ['No check in the catalog failed for this ref.'], false));
      return;
    }
    fails.forEach(function (item) {
      var box = document.createElement('div');
      box.className = 'agent-group';
      var head = document.createElement('div');
      head.className = 'agent-head';
      head.innerHTML = '<span class="aname">' + esc(item.agent.name) + '</span>';
      box.appendChild(head);
      box.appendChild(checkDetails(item.check));
      viewRoot.appendChild(box);
    });
  }

  function openEntry(entry) {
    var report = readReport(entry);
    if (!report) {
      setView('history');
      return;
    }
    state.report = report;
    state.entry = entry;
    state.feed = null;
    setSession(report);
    setRunState('done', 'complete · ' + report.score + '/100 (' + report.grade + ')');
    setView('task');
  }

  /* -------------------------------------------------------------- scan */
  function agentName(id) {
    try {
      var list = (window.CERBERUS_CHECKS && window.CERBERUS_CHECKS.agents) || [];
      for (var i = 0; i < list.length; i++) {
        if (list[i].id === id) return list[i].name || id;
      }
    } catch (e) {}
    return id;
  }

  function runScan(rawTarget) {
    if (state.runState === 'running') return;
    var target;
    try {
      target = window.CerberusScanner.parseTarget(rawTarget);
    } catch (e) {
      return failIdle('Could not parse target: ' + (e && e.message));
    }
    if (!target || target.kind !== 'github') {
      var hint = target && target.kind === 'website'
        ? 'Browsers cannot fetch arbitrary sites (CORS). Use the CLI: python3 examine.py "' + rawTarget + '"'
        : 'Give a GitHub URL or owner/repo — e.g. /scan murderszn/cerberus';
      return failIdle(hint);
    }
    var ctl = new AbortController();
    state.abort = ctl;
    state.feed = {
      target: { owner: target.owner, repo: target.repo, display: target.owner + '/' + target.repo },
      pct: 2, message: 'Starting…', groups: {}, agentOrder: []
    };
    state.report = null;
    state.entry = null;
    state.tree = null;
    state.openFile = null;
    setSession(null);
    sessionId.textContent = 'SESSION … / ' + target.owner + '/' + target.repo;
    setRunState('running', 'running');
    setView('task');

    function onProgress(ev) {
      if (!state.feed) return;
      state.feed.pct = Math.max(0, Math.min(100, ev.pct || 0));
      if (ev.message) state.feed.message = ev.message;
      if (ev.phase === 'check' && ev.agentId) {
        // One event per evaluated check: append it, newest last.
        var g = state.feed.groups[ev.agentId];
        if (!g) {
          g = state.feed.groups[ev.agentId] = { name: agentName(ev.agentId), done: 0, total: 0, checks: [] };
          state.feed.agentOrder.push(ev.agentId);
        }
        g.total++;
        g.done++;
        g.checks.push({
          id: ev.checkId, name: ev.checkName, status: ev.status === 'fail' ? 'fail' : 'pass',
          severity: '', summary: ev.status === 'fail' ? 'Failed — full detail loads when the scan completes.' : 'Passed.',
          findings: []
        });
      }
      if (state.view === 'task') renderFeed();
    }

    window.CerberusScanner.scan(target, { onProgress: onProgress, source: 'ink-terminal', signal: ctl.signal })
      .then(function (report) {
        state.abort = null;
        state.feed = null;
        state.report = report;
        state.entry = saveReport(report);
        setSession(report);
        setRunState('done', 'complete · ' + report.score + '/100 (' + report.grade + ')');
        render();
      })
      .catch(function (err) {
        state.abort = null;
        state.feed = null;
        var code = (err && err.code) || 'ERROR';
        if (code === 'ABORTED') setRunState('stopped', 'stopped');
        else setRunState('failed', 'failed · ' + code);
        render();
        if (code === 'ABORTED') {
          notice('Scan stopped. Partial results were discarded — nothing was saved.');
        } else {
          notice('Scan failed [' + code + ']: ' + (err && err.message));
        }
      });
  }

  function failIdle(message) {
    setRunState('idle', 'idle');
    render();
    notice(message);
  }

  function notice(message) {
    if (state.view !== 'task') setView('task');
    var d = document.createElement('p');
    d.className = 'msg';
    d.textContent = message;
    viewRoot.appendChild(d);
    stickBottom();
  }

  function stopRun() {
    if (state.abort) { try { state.abort.abort(); } catch (e) {} }
  }

  /* -------------------------------------------------------------- files */
  function treeKeyFor(report) {
    return report.target.owner + '/' + report.target.repo + '@' + report.target.sha;
  }

  function flaggedPaths() {
    var set = {};
    if (!state.report) return set;
    state.report.agents.forEach(function (a) {
      (a.checks || []).forEach(function (c) {
        (c.findings || []).forEach(function (f) { if (f.path) set[f.path] = true; });
      });
    });
    return set;
  }

  function renderFiles() {
    viewRoot.innerHTML = '';
    if (!state.report) {
      viewRoot.appendChild(emptyBox('No repository loaded', [
        'Run /scan owner/repo first — the file tree comes from that repository.',
        'Private repositories need a token: /token <pat> (kept in this tab only).'
      ], false));
      return;
    }
    var key = treeKeyFor(state.report);
    if (!state.tree || state.treeKey !== key) {
      viewRoot.appendChild(emptyBox('File tree not fetched yet', ['Fetching…'], false));
      fetchTree(state.report);
      return;
    }
    var h = document.createElement('p');
    h.className = 'section-label';
    h.textContent = 'FILES · ' + state.tree.paths.length + ' PATHS';
    viewRoot.appendChild(h);
    var flagged = flaggedPaths();
    var tree = document.createElement('div');
    tree.className = 'tree';
    tree.setAttribute('role', 'tree');
    tree.appendChild(buildTree(state.tree.paths, flagged));
    viewRoot.appendChild(tree);
    if (state.openFile) renderFileViewer();
  }

  function fetchTree(report) {
    var t = report.target;
    var url = 'https://api.github.com/repos/' + t.owner + '/' + t.repo +
      '/git/trees/' + (t.sha || t.ref || 'HEAD') + '?recursive=1';
    ghJSON(url)
      .then(function (j) {
        var paths = (j.tree || []).filter(function (n) { return n.type === 'blob'; })
          .map(function (n) { return n.path; }).sort();
        // Honest truncation: trees can be huge; cap display, say so.
        var truncated = paths.length > 4000;
        state.tree = { paths: paths.slice(0, 4000), truncated: truncated };
        state.treeKey = treeKeyFor(report);
        if (state.view === 'files') render();
      })
      .catch(function (err) {
        viewRoot.innerHTML = '';
        viewRoot.appendChild(emptyBox('Could not load the file tree', [String((err && err.message) || err)], false));
      });
  }

  function buildTree(paths, flagged) {
    // Nested <ul> from flat paths; folders collapsible, files open the viewer.
    var root = {};
    paths.forEach(function (p) {
      var parts = p.split('/'), node = root;
      for (var i = 0; i < parts.length; i++) {
        var last = i === parts.length - 1;
        node[parts[i]] = node[parts[i]] || (last ? { __file: p } : {});
        node = node[parts[i]];
      }
    });
    function ul(node) {
      var list = document.createElement('ul');
      list.setAttribute('role', 'group');
      Object.keys(node).sort().forEach(function (name) {
        var child = node[name];
        var li = document.createElement('li');
        if (child.__file) {
          var b = document.createElement('button');
          b.type = 'button';
          b.setAttribute('role', 'treeitem');
          b.textContent = name;
          if (flagged[child.__file]) { b.classList.add('flagged'); b.title = 'Has scan findings'; }
          (function (path) {
            b.addEventListener('click', function () { openFile(path); });
          })(child.__file);
          li.appendChild(b);
        } else {
          var f = document.createElement('button');
          f.type = 'button';
          f.textContent = name + '/';
          f.setAttribute('aria-expanded', 'true');
          var sub = ul(child);
          f.addEventListener('click', function () {
            var open = f.getAttribute('aria-expanded') === 'true';
            f.setAttribute('aria-expanded', open ? 'false' : 'true');
            sub.hidden = open;
          });
          li.appendChild(f);
          li.appendChild(sub);
        }
        list.appendChild(li);
      });
      return list;
    }
    return ul(root);
  }

  function openFile(path) {
    state.openFile = { path: path, status: 'loading', lines: [] };
    render();
    var t = state.report.target;
    var url = 'https://raw.githubusercontent.com/' + t.owner + '/' + t.repo + '/' + (t.sha || t.ref || 'HEAD') + '/' + path;
    fetch(url).then(function (r) {
      if (!r.ok) throw new Error('http ' + r.status);
      return r.text();
    }).then(function (text) {
      if (!state.openFile || state.openFile.path !== path) return;
      var lines = text.split('\n').slice(0, 2000);
      if (lines.length && lines[lines.length - 1] === '') lines.pop();
      state.openFile = { path: path, status: 'ok', lines: lines };
      if (state.view === 'files') render();
    }).catch(function () {
      if (!state.openFile || state.openFile.path !== path) return;
      state.openFile = { path: path, status: 'error', lines: [] };
      if (state.view === 'files') render();
    });
  }

  function renderFileViewer() {
    var f = state.openFile;
    var box = document.createElement('div');
    box.className = 'fileview';
    var head = document.createElement('header');
    var title = document.createElement('span');
    title.textContent = f.path;
    var close = document.createElement('button');
    close.type = 'button';
    close.textContent = 'close';
    close.addEventListener('click', function () { state.openFile = null; render(); });
    head.appendChild(title);
    head.appendChild(close);
    box.appendChild(head);
    if (f.status === 'loading') {
      var p = document.createElement('p');
      p.className = 'status-line';
      p.textContent = 'Loading file…';
      box.appendChild(p);
    } else if (f.status === 'error') {
      var e = document.createElement('p');
      e.className = 'status-line';
      e.textContent = 'Could not fetch this file (binary, too large, or removed upstream).';
      box.appendChild(e);
    } else {
      var hits = {};
      (state.report.agents || []).forEach(function (a) {
        (a.checks || []).forEach(function (c) {
          (c.findings || []).forEach(function (fd) {
            if (fd.path === f.path && fd.line) hits[fd.line] = true;
          });
        });
      });
      var ol = document.createElement('ol');
      f.lines.forEach(function (ln, i) {
        var li = document.createElement('li');
        if (hits[i + 1]) { li.classList.add('hit'); li.title = 'Line cited by a scan finding'; }
        li.textContent = ln || ' ';
        ol.appendChild(li);
      });
      box.appendChild(ol);
    }
    viewRoot.appendChild(box);
    if (box.scrollIntoView) { try { box.scrollIntoView({ block: 'nearest' }); } catch (e) {} }
  }

  /* ------------------------------------------------------------ changes */
  function renderChanges() {
    viewRoot.innerHTML = '';
    if (!state.report) {
      viewRoot.appendChild(emptyBox('No scan loaded', [
        'Run /scan owner/repo or open a report from History.',
        'Changes lists files cited by scan findings — unified diffs need the CLI.'
      ], false));
      return;
    }
    var byFile = {};
    state.report.agents.forEach(function (a) {
      (a.checks || []).forEach(function (c) {
        if (c.status !== 'fail') return;
        (c.findings || []).forEach(function (f) {
          var p = f.path || '(location withheld)';
          (byFile[p] = byFile[p] || []).push({ agent: a.name, check: c, finding: f });
        });
      });
    });
    var files = Object.keys(byFile).sort();
    var h = document.createElement('p');
    h.className = 'section-label';
    h.textContent = 'CHANGES · ' + files.length + ' FILES CITED · FROM LATEST SCAN';
    viewRoot.appendChild(h);
    var note = document.createElement('p');
    note.className = 'hist-sub';
    note.textContent = 'Scan findings grouped by file — not version-control diffs. Unified diffs need the CLI (cerberus agent --pr).';
    viewRoot.appendChild(note);
    if (!files.length) {
      viewRoot.appendChild(emptyBox('No cited files', ['The latest scan failed no checks with file locations.'], false));
      return;
    }
    files.forEach(function (p) {
      var items = byFile[p];
      var d = document.createElement('details');
      d.className = 'check';
      if (p !== '(location withheld)') d.open = false;
      var worst = items.some(function (it) { return it.check.severity === 'critical'; }) ? 'critical'
        : items.some(function (it) { return it.check.severity === 'high'; }) ? 'high' : 'noted';
      var s = document.createElement('summary');
      s.innerHTML = '<span class="cid">' + esc(p) + '</span>' +
        '<span class="cstat" data-s="' + (worst === 'noted' ? 'pass' : 'fail') + '">' +
        esc(items.length + ' finding' + (items.length === 1 ? '' : 's')) + '</span>';
      d.appendChild(s);
      var body = document.createElement('div');
      body.className = 'check-body';
      body.innerHTML = items.map(function (it) {
        return '<p><span class="lbl">' + esc(it.check.id + ' · ' + it.agent) + ' </span>' +
          esc(it.check.name) + '</p>' + findingHTML(it.finding, it.check.severity);
      }).join('');
      d.appendChild(body);
      viewRoot.appendChild(d);
    });
  }

  /* ------------------------------------------------------------ history */
  function renderHistory() {
    viewRoot.innerHTML = '';
    var h = document.createElement('p');
    h.className = 'section-label';
    h.textContent = 'HISTORY · SHARED WITH THE CERBERUS AGENT PAGE';
    viewRoot.appendChild(h);
    var idx = readIndex();
    if (!idx.length) {
      viewRoot.appendChild(emptyBox('No saved sessions', [
        'Completed scans are stored in this browser and listed here.',
        'Run /scan owner/repo to create the first entry.'
      ], false));
      return;
    }
    idx.forEach(function (entry) {
      var row = document.createElement('button');
      row.type = 'button';
      row.className = 'hist-row';
      var ok = entry.grade && entry.grade[0] <= 'B';
      row.innerHTML = '<span class="tick" aria-hidden="true">' + (ok ? '✓' : '✖') + '</span>' +
        '<span>' + esc(entry.display) + ' · ' + esc(String(entry.score)) + '/100 (' + esc(entry.grade) + ')' +
        '<span class="sub">' + esc(entry.sha ? shortSha(entry.sha) : '') + ' · ' + esc(fmtTime(entry.scannedAt)) + '</span></span>' +
        '<span class="meta">open →</span>';
      row.addEventListener('click', function () { openEntry(entry); });
      viewRoot.appendChild(row);
      var sub = document.createElement('div');
      var rescan = document.createElement('button');
      rescan.type = 'button';
      rescan.className = 'hist-row';
      rescan.innerHTML = '<span class="tick" aria-hidden="true">↻</span><span>Rescan ' + esc(entry.display) + '</span>';
      rescan.addEventListener('click', function (ev) {
        ev.stopPropagation();
        composer.value = '/scan ' + entry.display;
        composer.focus();
      });
      sub.appendChild(rescan);
      viewRoot.appendChild(sub);
    });
  }

  /* ------------------------------------------------------------ composer */
  var COMMANDS = [
    { name: '/scan owner/repo', hint: 'Run a real security scan', run: function (arg) { runScan(arg); } },
    { name: '/open owner/repo', hint: 'Open latest saved report', run: function (arg) {
      var t = window.CerberusScanner.parseTarget(arg || '');
      var idx = readIndex();
      var hit = idx.filter(function (e) { return t.kind === 'github' && e.owner === t.owner && e.repo === t.repo; })[0];
      if (hit) openEntry(hit);
      else notice('No saved report for ' + (arg || 'that target') + '. Run /scan first.');
    } },
    { name: '/files', hint: 'Browse the loaded repository', run: function () { setView('files'); } },
    { name: '/changes', hint: 'Findings grouped by file', run: function () { setView('changes'); } },
    { name: '/history', hint: 'Saved scan sessions', run: function () { setView('history'); } },
    { name: '/task', hint: 'Back to the current task', run: function () { setView('task'); } },
    { name: '/token', hint: '/token <pat> — tab-only GitHub token', run: function (arg) {
      try {
        if (arg) { sessionStorage.setItem(PAT_KEY, arg); notice('Token kept for this tab only. Connection re-checking…'); }
        else { sessionStorage.removeItem(PAT_KEY); notice('Tab token cleared.'); }
      } catch (e) { notice('Could not store the token in this browser.'); }
      checkConnection();
    } },
    { name: '/stop', hint: 'Stop the running scan', run: function () { stopRun(); } },
    { name: '/clear', hint: 'Clear this view', run: function () {
      state.feed = null; state.report = null; state.entry = null;
      setSession(null); setRunState('idle', 'idle'); render();
    } },
    { name: '/help', hint: 'List commands', run: function () {
      var d = document.createElement('div');
      d.className = 'msg';
      d.innerHTML = '<p><span class="lbl">COMMANDS</span></p><p>' +
        COMMANDS.map(function (c) { return '<code>' + esc(c.name) + '</code> — ' + esc(c.hint); }).join('<br />') +
        '</p><p>Plain text is saved as a local task note (LOCAL) — execution happens in the CLI: <code>cerberus agent "…"</code>.</p>';
      if (state.view !== 'task') setView('task');
      viewRoot.appendChild(d);
      stickBottom();
    } }
  ];

  function matchCommand(text) {
    var cmd = text.trim().split(/\s+/)[0].toLowerCase();
    for (var i = 0; i < COMMANDS.length; i++) {
      if (COMMANDS[i].name.split(' ')[0] === cmd) return COMMANDS[i];
    }
    return null;
  }

  function submitComposer() {
    var text = composer.value.trim();
    if (!text) return;
    var cmd = matchCommand(text);
    if (state.runState === 'running' && (!cmd || cmd.name.split(' ')[0] !== '/stop')) {
      notice('A scan is already running — STOP it first, or wait for it to finish.');
      return;
    }
    composer.value = '';
    try { sessionStorage.setItem(DRAFT_KEY, ''); } catch (e) {}
    autosize();
    if (cmd) {
      var arg = text.slice(text.trim().split(/\s+/)[0].length).trim();
      cmd.run(arg);
      return;
    }
    // Plain task text: honest local note, never fake execution.
    var tasks = readTasks();
    tasks.unshift({ text: text, createdAt: new Date().toISOString() });
    writeJSON(TASKS_KEY, tasks.slice(0, 20));
    if (state.view !== 'task') setView('task');
    state.report = null; state.feed = null;
    setSession(null); setRunState('idle', 'idle');
    render();
    notice('Saved locally (LOCAL). To execute it, run: cerberus agent "' +
      (text.length > 80 ? text.slice(0, 80) + '…' : text) + '"');
  }

  function autosize() {
    composer.style.height = 'auto';
    composer.style.height = Math.min(160, Math.max(56, composer.scrollHeight)) + 'px';
  }

  /* ------------------------------------------------------------ palette */
  var paletteVeil, paletteInput, paletteList, paletteItems = [], paletteSel = 0;

  function paletteEntries(filter) {
    var f = (filter || '').toLowerCase();
    var out = [];
    COMMANDS.forEach(function (c) { out.push({ label: c.name, hint: c.hint, kind: 'command', run: function () {
      composer.value = c.name.split(' ')[0] + ' ';
      composer.focus();
      closePalette();
    } }); });
    ['task', 'files', 'changes', 'history'].forEach(function (v, i) {
      out.push({ label: '0' + (i + 1) + ' / ' + v, hint: 'go to view', kind: 'view', run: function () { setView(v); } });
    });
    readIndex().slice(0, 6).forEach(function (e) {
      out.push({ label: e.display + ' · ' + e.score + '/100', hint: 'open report', kind: 'report', run: function () { openEntry(e); } });
    });
    if (!f) return out;
    return out.filter(function (it) { return (it.label + ' ' + it.hint).toLowerCase().indexOf(f) !== -1; });
  }

  function openPalette() {
    paletteVeil.hidden = false;
    paletteInput.value = '';
    renderPalette('');
    paletteInput.focus();
  }
  function closePalette() {
    paletteVeil.hidden = true;
    composer.focus();
  }
  function renderPalette(filter) {
    paletteItems = paletteEntries(filter);
    paletteSel = 0;
    paletteList.innerHTML = '';
    if (!paletteItems.length) {
      var li = document.createElement('li');
      li.innerHTML = '<button type="button" disabled><span>No matches</span></button>';
      paletteList.appendChild(li);
      return;
    }
    paletteItems.forEach(function (it, i) {
      var li = document.createElement('li');
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('role', 'option');
      b.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      b.innerHTML = '<span>' + esc(it.label) + '</span><span class="kind">' + esc(it.kind) + '</span>';
      b.addEventListener('click', function () { closePalette(); it.run(); });
      b.addEventListener('mousemove', function () { setPaletteSel(i); });
      li.appendChild(b);
      paletteList.appendChild(li);
    });
  }
  function setPaletteSel(i) {
    paletteSel = (i + paletteItems.length) % Math.max(1, paletteItems.length);
    $all('button', paletteList).forEach(function (b, j) {
      b.setAttribute('aria-selected', j === paletteSel ? 'true' : 'false');
    });
  }

  /* ------------------------------------------------------------ keyboard */
  document.addEventListener('keydown', function (ev) {
    var inField = /^(TEXTAREA|INPUT)$/.test((document.activeElement || {}).tagName || '');
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'k') {
      ev.preventDefault();
      if (paletteVeil.hidden) openPalette(); else closePalette();
      return;
    }
    if (!paletteVeil.hidden) {
      if (ev.key === 'Escape') { ev.preventDefault(); closePalette(); }
      else if (ev.key === 'ArrowDown') { ev.preventDefault(); setPaletteSel(paletteSel + 1); }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); setPaletteSel(paletteSel - 1); }
      else if (ev.key === 'Enter' && paletteItems[paletteSel]) {
        ev.preventDefault();
        var it = paletteItems[paletteSel];
        closePalette(); it.run();
      }
      return;
    }
    if (ev.key === '/' && !inField) {
      ev.preventDefault();
      composer.focus();
      return;
    }
    if (ev.key === 'Escape' && state.runState === 'running') {
      ev.preventDefault();
      stopRun();
    }
  });

  /* ---------------------------------------------------------------- init */
  function checkConnection() {
    envState.setAttribute('data-state', 'checking');
    envText.textContent = 'local / checking';
    probeConnection(function (st, text) {
      envState.setAttribute('data-state', st);
      envText.textContent = text;
    });
  }

  function init() {
    work = $('#work'); viewRoot = $('#viewRoot');
    sessionId = $('#sessionId'); sessionState = $('#sessionState');
    envState = $('#envState'); envText = $('#envText');
    composer = $('#composer'); composerForm = $('#composerForm');
    sendBtn = $('#sendBtn'); stopBtn = $('#stopBtn');
    sideNav = $('#sideNav'); sideFoot = $('#sideFoot');
    paletteVeil = $('#paletteVeil'); paletteInput = $('#paletteInput'); paletteList = $('#paletteList');

    $all('.side-item', sideNav).forEach(function (b) {
      b.addEventListener('click', function () { setView(b.getAttribute('data-view')); });
    });
    stopBtn.addEventListener('click', stopRun);
    composerForm.addEventListener('submit', function (ev) { ev.preventDefault(); submitComposer(); });
    composer.addEventListener('input', function () {
      autosize();
      try { sessionStorage.setItem(DRAFT_KEY, composer.value); } catch (e) {}
    });
    composer.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); submitComposer(); }
    });
    try {
      var draft = sessionStorage.getItem(DRAFT_KEY);
      if (draft) { composer.value = draft; autosize(); }
    } catch (e) {}
    paletteInput.addEventListener('input', function () { renderPalette(paletteInput.value); });
    $('#paletteBtn').addEventListener('click', openPalette);
    paletteVeil.addEventListener('click', function (ev) { if (ev.target === paletteVeil) closePalette(); });

    window.addEventListener('online', checkConnection);
    window.addEventListener('offline', checkConnection);
    checkConnection();
    setRunState('idle', 'idle');
    setSession(null);
    render();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
