// Cerberus scan engine — plain ES2018, no imports, no bundler, no external deps.
// Exposes window.CerberusScanner = { parseTarget(input), scan(target, opts) }.
// See docs/IMPROVEMENTS.md §3 for the interface contract this file implements.
(function (global) {
  'use strict';

  var ENGINE_VERSION = '2.0.0';

  // ---------------------------------------------------------------------
  // Typed errors
  // ---------------------------------------------------------------------
  function ScanError(code, message, extra) {
    var err = new Error(message || code);
    err.code = code;
    if (extra) {
      for (var k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) err[k] = extra[k];
    }
    return err;
  }

  // ---------------------------------------------------------------------
  // Glob matching: '*' does not cross '/', '**' does, '?' matches one char.
  // ---------------------------------------------------------------------
  var GLOB_CACHE = Object.create(null);

  function globToRegExp(glob) {
    if (GLOB_CACHE[glob]) return GLOB_CACHE[glob];
    var re = '';
    var i = 0;
    var n = glob.length;
    while (i < n) {
      var c = glob[i];
      if (c === '*') {
        if (glob[i + 1] === '*') {
          // '**'
          if (glob[i + 2] === '/') {
            re += '(?:.*/)?';
            i += 3;
            continue;
          } else {
            re += '.*';
            i += 2;
            continue;
          }
        } else {
          re += '[^/]*';
          i += 1;
          continue;
        }
      } else if (c === '?') {
        re += '[^/]';
        i += 1;
        continue;
      } else if ('.+^${}()|[]\\'.indexOf(c) !== -1) {
        re += '\\' + c;
        i += 1;
        continue;
      } else {
        re += c;
        i += 1;
        continue;
      }
    }
    var compiled = new RegExp('^' + re + '$');
    GLOB_CACHE[glob] = compiled;
    return compiled;
  }

  function globMatch(path, glob) {
    return globToRegExp(glob).test(path);
  }

  function matchesAny(path, globs) {
    if (!globs) return false;
    for (var i = 0; i < globs.length; i++) {
      if (globMatch(path, globs[i])) return true;
    }
    return false;
  }

  // ---------------------------------------------------------------------
  // Target parsing
  // ---------------------------------------------------------------------
  function parseTarget(input) {
    var raw = (input || '').trim();
    if (!raw) return { kind: 'unknown' };

    // SSH form: git@github.com:owner/repo.git
    var sshMatch = raw.match(/^git@github\.com:([^\/]+)\/([^\/]+?)(?:\.git)?\/?$/i);
    if (sshMatch) {
      return { kind: 'github', owner: sshMatch[1], repo: sshMatch[2], ref: null };
    }

    if (/^https?:\/\//i.test(raw)) {
      var url;
      try {
        url = new URL(raw);
      } catch (e) {
        return { kind: 'unknown' };
      }
      var host = url.hostname.replace(/^www\./i, '').toLowerCase();
      if (host === 'github.com') {
        var parts = url.pathname.replace(/^\/+|\/+$/g, '').split('/').filter(Boolean);
        if (parts.length < 2) return { kind: 'unknown', url: raw };
        var owner = parts[0];
        var repo = parts[1].replace(/\.git$/i, '');
        var ref = null;
        if (parts.length >= 4 && parts[2] === 'tree') {
          ref = decodeURIComponent(parts.slice(3).join('/'));
        }
        return { kind: 'github', owner: owner, repo: repo, ref: ref, url: raw };
      }
      return { kind: 'website', url: raw };
    }

    // bare owner/repo shorthand (exactly two segments, no protocol, no leading '@')
    var bareMatch = raw.match(/^([A-Za-z0-9._-]+)\/([A-Za-z0-9._-]+?)(?:\.git)?$/);
    if (bareMatch && raw.indexOf('@') !== 0 && raw.indexOf(' ') === -1) {
      return { kind: 'github', owner: bareMatch[1], repo: bareMatch[2], ref: null };
    }

    // npm/pypi-style package identifiers: @scope/name, or plain-name[==version|@version]
    if (/^@[A-Za-z0-9._-]+\/[A-Za-z0-9._-]+$/.test(raw)) {
      return { kind: 'package', url: raw };
    }
    if (/^[A-Za-z0-9][A-Za-z0-9._-]*(?:(?:==|>=|<=|~=|@)[A-Za-z0-9.\-]+)?$/.test(raw) && raw.indexOf('/') === -1) {
      return { kind: 'package', url: raw };
    }

    return { kind: 'unknown' };
  }

  // ---------------------------------------------------------------------
  // Placeholder detection
  // ---------------------------------------------------------------------
  function isPlaceholder(text, placeholderPatternStr) {
    if (!placeholderPatternStr) return false;
    try {
      var re = new RegExp(placeholderPatternStr, 'i');
      return re.test(text);
    } catch (e) {
      return false;
    }
  }

  // ---------------------------------------------------------------------
  // Line index helpers
  // ---------------------------------------------------------------------
  function buildLineStarts(content) {
    var starts = [0];
    for (var i = 0; i < content.length; i++) {
      if (content.charCodeAt(i) === 10) starts.push(i + 1);
    }
    return starts;
  }

  function lineColFromIndex(lineStarts, idx) {
    var lo = 0, hi = lineStarts.length - 1, ans = 0;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (lineStarts[mid] <= idx) { ans = mid; lo = mid + 1; } else hi = mid - 1;
    }
    return { line: ans + 1, col: idx - lineStarts[ans] + 1, lineStart: lineStarts[ans] };
  }

  function lineTextAt(content, lineStart) {
    var end = content.indexOf('\n', lineStart);
    if (end === -1) end = content.length;
    var text = content.slice(lineStart, end);
    if (text.charAt(text.length - 1) === '\r') text = text.slice(0, -1);
    return text;
  }

  // Line-level comment heuristic covering the languages the catalog targets:
  // #  (Python, Ruby, YAML, shell, Dockerfile)   //  (C-family, JS/TS, Go, Java)
  // *  (inside a block comment)                  <!-- (HTML, XML, Markdown)
  // -- (SQL, Lua)
  // Deliberately only recognises a comment that OPENS the line. A trailing comment after
  // real code still gets scanned, because the code before it executes.
  var COMMENT_LINE_RE = /^\s*(#|\/\/|\/\*|\*(?!\/)|\*\/|<!--|--(?!\s*\[)|;|%)/;
  function isCommentLine(lineText) {
    return COMMENT_LINE_RE.test(lineText);
  }

  function trim200(text) {
    if (text.length <= 200) return text;
    return text.slice(0, 200) + '…';
  }

  function trimMatch(text) {
    if (text.length <= 160) return text;
    return text.slice(0, 160) + '…';
  }

  // ---------------------------------------------------------------------
  // Regex building from catalog fields (pattern + flags, always global)
  // ---------------------------------------------------------------------
  function buildRegExp(pattern, flagsStr) {
    var flags = flagsStr || '';
    if (flags.indexOf('g') === -1) flags += 'g';
    return new RegExp(pattern, flags);
  }

  // ---------------------------------------------------------------------
  // GitHub API / raw content fetch helpers
  // ---------------------------------------------------------------------
  function rateLimitInfo(headers) {
    var remaining = headers.get('x-ratelimit-remaining');
    var reset = headers.get('x-ratelimit-reset');
    return {
      remaining: remaining !== null ? parseInt(remaining, 10) : null,
      resetAt: reset !== null ? new Date(parseInt(reset, 10) * 1000).toISOString() : null
    };
  }

  function ghApiFetch(url, token, signal) {
    var headers = { 'Accept': 'application/vnd.github+json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return fetch(url, { headers: headers, signal: signal }).then(function (resp) {
      var rl = rateLimitInfo(resp.headers);
      if (resp.status === 403 && rl.remaining === 0) {
        throw ScanError('RATE_LIMITED', 'GitHub API rate limit exceeded.', { resetAt: rl.resetAt });
      }
      if (resp.status === 404) {
        throw ScanError('NOT_FOUND', 'Repository, branch, or resource not found (or private).');
      }
      if (!resp.ok) {
        throw ScanError('NETWORK', 'GitHub API request failed with status ' + resp.status + ' for ' + url);
      }
      return resp.json().then(function (json) {
        return { json: json, rateLimit: rl };
      });
    }, function (err) {
      if (err && err.code) throw err;
      throw ScanError('NETWORK', 'Network error contacting GitHub API: ' + (err && err.message));
    });
  }

  function rawFetch(url, signal) {
    return fetch(url, { signal: signal }).then(function (resp) {
      if (!resp.ok) {
        var e = new Error('raw fetch failed with status ' + resp.status);
        e.status = resp.status;
        throw e;
      }
      return resp.text();
    });
  }

  // ---------------------------------------------------------------------
  // Concurrency pool
  // ---------------------------------------------------------------------
  function runPool(items, concurrency, worker) {
    return new Promise(function (resolve) {
      var idx = 0;
      var active = 0;
      var results = new Array(items.length);
      var done = 0;
      if (items.length === 0) { resolve(results); return; }
      function next() {
        if (idx >= items.length) {
          if (active === 0) resolve(results);
          return;
        }
        var myIdx = idx++;
        active++;
        Promise.resolve(worker(items[myIdx], myIdx)).then(function (r) {
          results[myIdx] = r;
        }).catch(function (e) {
          results[myIdx] = { error: e };
        }).then(function () {
          active--;
          done++;
          next();
        });
      }
      var starters = Math.min(concurrency, items.length);
      for (var i = 0; i < starters; i++) next();
    });
  }

  // ---------------------------------------------------------------------
  // File priority ranking
  // ---------------------------------------------------------------------
  var MANIFEST_BASENAMES = [
    'package.json', 'requirements.txt', 'pyproject.toml', 'Pipfile', 'Gemfile',
    'composer.json', 'go.mod', 'Cargo.toml', 'pom.xml', 'build.gradle',
    'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml', '.gitignore',
    '.env', 'Makefile', 'tsconfig.json', 'webpack.config.js', 'vite.config.js'
  ];
  var PRIORITY_DIRS = ['src/', 'app/', 'lib/', 'api/'];

  function priorityRank(path) {
    var base = path.indexOf('/') === -1 ? path : path.slice(path.lastIndexOf('/') + 1);
    if (MANIFEST_BASENAMES.indexOf(base) !== -1) return 0;
    if (base.indexOf('Dockerfile') === 0 || /\.tf$/.test(base)) return 0;
    if (path.indexOf('/') === -1) return 1; // top-level
    for (var i = 0; i < PRIORITY_DIRS.length; i++) {
      if (path.indexOf(PRIORITY_DIRS[i]) === 0) return 2;
    }
    return 3;
  }

  // ---------------------------------------------------------------------
  // Acquisition
  // ---------------------------------------------------------------------
  // Per-repo suppression. Mirrors parse_cerberusignore() in examine.py — keep in lockstep.
  var CERBERUSIGNORE = '.cerberusignore';

  function parseCerberusIgnore(text) {
    var patterns = [];
    text.split('\n').forEach(function (raw) {
      var line = raw.trim();
      if (!line || line.charAt(0) === '#') return;
      line = line.replace(/\/+$/, '');
      if (line.indexOf('/') === -1 && line.indexOf('**') !== 0) {
        patterns.push('**/' + line);
        patterns.push('**/' + line + '/**');
      } else {
        patterns.push(line);
        patterns.push(line.replace(/\*+$/, '').replace(/\/+$/, '') + '/**');
      }
    });
    return patterns;
  }

  function fetchRawFile(target, sha, path) {
    var url = 'https://raw.githubusercontent.com/' + encodeURIComponent(target.owner) +
      '/' + encodeURIComponent(target.repo) + '/' + sha + '/' + path;
    return fetch(url).then(function (res) {
      if (!res.ok) return null;
      return res.text();
    });
  }

  var FILE_BUDGET = 1200;
  var SIZE_BUDGET = 512 * 1024;
  var TIME_BUDGET_MS = 120 * 1000;
  var CONCURRENCY = 12;

  function buildCandidateGlobs(catalog) {
    var set = {};
    (catalog.source_globs || []).forEach(function (g) { set[g] = true; });
    (catalog.checks || []).forEach(function (ch) {
      var d = ch.detector || {};
      if (d.include) d.include.forEach(function (g) { set[g] = true; });
      if (d.kind === 'content_required' && d.paths) d.paths.forEach(function (g) { set[g] = true; });
    });
    return Object.keys(set);
  }

  function acquireRepo(target, opts, onProgress) {
    var token = opts && opts.token;
    var signal = opts && opts.signal;
    var startTime = Date.now();
    var apiBase = 'https://api.github.com/repos/' + encodeURIComponent(target.owner) + '/' + encodeURIComponent(target.repo);
    var lastRateLimit = null;

    onProgress({ phase: 'resolving', pct: 2, message: 'Resolving ' + target.owner + '/' + target.repo + '…' });

    return ghApiFetch(apiBase, token, signal).then(function (result) {
      lastRateLimit = result.rateLimit;
      var repoMeta = result.json;
      var ref = target.ref || repoMeta.default_branch;

      onProgress({ phase: 'resolving', pct: 6, message: 'Resolving ref ' + ref + '…' });

      return ghApiFetch(apiBase + '/commits/' + encodeURIComponent(ref), token, signal).then(function (commitResult) {
        lastRateLimit = commitResult.rateLimit;
        var sha = commitResult.json.sha;

        onProgress({ phase: 'tree', pct: 12, message: 'Fetching file tree…' });

        return ghApiFetch(apiBase + '/git/trees/' + sha + '?recursive=1', token, signal).then(function (treeResult) {
          lastRateLimit = treeResult.rateLimit;
          var treeJson = treeResult.json;
          var truncated = !!treeJson.truncated;
          var allBlobs = (treeJson.tree || []).filter(function (e) { return e.type === 'blob'; });
          var allPaths = allBlobs.map(function (e) { return e.path; });

          return {
            repoMeta: repoMeta, ref: ref, sha: sha, allBlobs: allBlobs, allPaths: allPaths,
            treeTruncated: truncated, rateLimit: lastRateLimit
          };
        });
      });
    }).then(function (base) {
      // A repo may suppress paths via .cerberusignore. Fetch it before deciding what is
      // eligible, so ignored files are never counted as coverage or fetched at all.
      var hasIgnore = base.allBlobs.some(function (b) { return b.path === CERBERUSIGNORE; });
      if (!hasIgnore) return { base: base, ignorePatterns: [] };
      return fetchRawFile(target, base.sha, CERBERUSIGNORE)
        .then(function (text) { return { base: base, ignorePatterns: parseCerberusIgnore(text || '') }; })
        .catch(function () { return { base: base, ignorePatterns: [] }; });
    }).then(function (wrapped) {
      var base = wrapped.base;
      var catalog = opts.catalog;
      var candidateGlobs = buildCandidateGlobs(catalog);
      var globalExclude = (catalog.global_exclude || []).concat(wrapped.ignorePatterns);

      var eligible = base.allBlobs.filter(function (b) {
        if (matchesAny(b.path, globalExclude)) return false;
        return matchesAny(b.path, candidateGlobs);
      });

      var tooLargeUpfront = eligible.filter(function (b) { return typeof b.size === 'number' && b.size > SIZE_BUDGET; });
      var fetchable = eligible.filter(function (b) { return !(typeof b.size === 'number' && b.size > SIZE_BUDGET); });

      fetchable.sort(function (a, b) {
        var ra = priorityRank(a.path), rb = priorityRank(b.path);
        if (ra !== rb) return ra - rb;
        return a.path < b.path ? -1 : (a.path > b.path ? 1 : 0);
      });

      var toFetch = fetchable.slice(0, FILE_BUDGET);
      var overBudget = fetchable.slice(FILE_BUDGET);

      var files = Object.create(null);
      var skipReasons = {};
      var bytesScanned = 0;
      var timeExceeded = false;

      function recordSkip(reason) {
        skipReasons[reason] = (skipReasons[reason] || 0) + 1;
      }

      tooLargeUpfront.forEach(function () { recordSkip('file_too_large'); });
      overBudget.forEach(function () { recordSkip('file_budget_exceeded'); });

      var rawBase = 'https://raw.githubusercontent.com/' + encodeURIComponent(target.owner) + '/' + encodeURIComponent(target.repo) + '/' + base.sha + '/';
      var fetchedCount = 0;

      onProgress({
        phase: 'fetching', pct: 20, message: 'Fetching file contents…',
        filesFetched: 0, filesTotal: toFetch.length
      });

      return runPool(toFetch, CONCURRENCY, function (blob) {
        if (Date.now() - startTime > TIME_BUDGET_MS) {
          timeExceeded = true;
          recordSkip('time_budget_exceeded');
          return null;
        }
        if (signal && signal.aborted) {
          throw ScanError('ABORTED', 'Scan aborted by caller.');
        }
        var pathParts = blob.path.split('/').map(encodeURIComponent).join('/');
        return rawFetch(rawBase + pathParts, signal).then(function (text) {
          if (text.length > SIZE_BUDGET) {
            recordSkip('file_too_large');
            return null;
          }
          bytesScanned += text.length;
          files[blob.path] = text;
          fetchedCount++;
          if (fetchedCount % 10 === 0 || fetchedCount === toFetch.length) {
            onProgress({
              phase: 'fetching',
              pct: 20 + Math.round((fetchedCount / Math.max(1, toFetch.length)) * 50),
              message: 'Fetching file contents… (' + fetchedCount + '/' + toFetch.length + ')',
              filesFetched: fetchedCount, filesTotal: toFetch.length
            });
          }
          return text;
        }, function (err) {
          recordSkip('fetch_error');
          return null;
        });
      }).then(function () {
        var filesSkipped = Object.keys(skipReasons).reduce(function (sum, k) { return sum + skipReasons[k]; }, 0);
        var notes = [];
        if (skipReasons.file_too_large) notes.push(skipReasons.file_too_large + ' file(s) exceeded the 512 KB limit and were not scanned.');
        if (skipReasons.file_budget_exceeded) notes.push(skipReasons.file_budget_exceeded + ' file(s) exceeded the 400-file scan budget and were not scanned.');
        if (skipReasons.time_budget_exceeded) notes.push('The 90 s acquisition time budget was reached before all files could be fetched.');
        if (skipReasons.fetch_error) notes.push(skipReasons.fetch_error + ' file(s) could not be fetched due to a network error.');
        if (base.treeTruncated) notes.push('The repository tree response was truncated by the GitHub API; some files may be missing from this scan.');

        return {
          repoMeta: base.repoMeta,
          ref: base.ref,
          sha: base.sha,
          allPaths: base.allPaths,
          eligiblePaths: eligible.map(function (b) { return b.path; }),
          files: files,
          coverage: {
            filesInTree: base.allPaths.length,
            filesEligible: eligible.length,
            filesScanned: Object.keys(files).length,
            filesSkipped: filesSkipped,
            bytesScanned: bytesScanned,
            truncated: base.treeTruncated || timeExceeded || skipReasons.file_budget_exceeded > 0,
            skipReasons: skipReasons
          },
          notes: notes,
          rateLimit: base.rateLimit
        };
      });
    });
  }

  // ---------------------------------------------------------------------
  // Evaluation helpers
  // ---------------------------------------------------------------------
  function pathsExistInTree(allPaths, globs) {
    for (var i = 0; i < allPaths.length; i++) {
      if (matchesAny(allPaths[i], globs)) return true;
    }
    return false;
  }

  var APPLIES_REASONS = {
    'W-02': 'No Dockerfile in repository',
    'W-03': 'No Dockerfile in repository',
    'W-08': 'No application source files found in repository',
    'L-01': 'No dependency manifest (package.json, requirements.txt, Gemfile, composer.json, or pyproject.toml) found in repository',
    'L-04': 'No dependency manifest found in repository',
    'V-07': 'No .gitignore file in repository',
    'R-02': 'No Terraform or CloudFormation configuration in repository'
  };

  function appliesIfReason(checkId, patterns) {
    if (APPLIES_REASONS[checkId]) return APPLIES_REASONS[checkId];
    return 'Precondition not met: no file matching ' + patterns.slice(0, 3).join(', ') + ' in repository';
  }

  var PATH_REQUIRED_REASONS = {
    'W-06': 'No SECURITY.md found in repository',
    'L-01': 'No dependency lockfile found in repository',
    'L-04': 'No Dependabot or Renovate configuration found in repository',
    'A-04': 'No continuous integration configuration found in repository',
    'R-04': 'No test files found in repository'
  };

  function pathRequiredReason(checkId, patterns) {
    if (PATH_REQUIRED_REASONS[checkId]) return PATH_REQUIRED_REASONS[checkId];
    return 'No file matching ' + patterns.slice(0, 3).join(', ') + ' found in repository';
  }

  function filterFilesForCheck(check, eligiblePaths, catalog) {
    var det = check.detector;
    var pool = eligiblePaths;
    if (det.include) pool = pool.filter(function (p) { return matchesAny(p, det.include); });
    if (det.paths && det.kind === 'content_required') pool = pool.filter(function (p) { return matchesAny(p, det.paths); });
    if (det.exclude) pool = pool.filter(function (p) { return !matchesAny(p, det.exclude); });
    if (det.exclude_tests) pool = pool.filter(function (p) { return !matchesAny(p, catalog.test_paths || []); });
    return pool;
  }

  function permalink(target, sha, path, line) {
    return 'https://github.com/' + target.owner + '/' + target.repo + '/blob/' + sha + '/' + path + '#L' + line;
  }

  function scanFileForPattern(check, catalog, path, content, lineStarts, target, sha, out) {
    var det = check.detector;
    var re;
    try {
      re = buildRegExp(det.pattern, det.flags);
    } catch (e) {
      return { invalid: true };
    }
    var notMatchRe = null;
    if (det.not_match) {
      try { notMatchRe = new RegExp(det.not_match, 'i'); } catch (e) { notMatchRe = null; }
    }
    var m;
    var guard = 0;
    re.lastIndex = 0;
    while ((m = re.exec(content)) !== null) {
      guard++;
      if (guard > 20000) break; // pathological-file safety valve
      if (m[0].length === 0) {
        re.lastIndex++;
        if (re.lastIndex > content.length) break;
        continue;
      }
      var loc = lineColFromIndex(lineStarts, m.index);
      var lineText = lineTextAt(content, loc.lineStart);

      // Commented-out code is not executed, so a behavioural finding on a comment line is
      // noise (a disabled `curl | bash` CI step is not a live risk). Secret-detection checks
      // opt out via `scan_comments`, because a credential pasted into a comment is still a
      // leaked credential.
      if (!det.scan_comments && isCommentLine(lineText)) continue;

      // `not_match` normally tests just the matched line. Some sinks are written as a
      // multi-line expression (a template assignment continued over several lines), where
      // the mitigation sits below the line that matched. `not_match_window` opts a check
      // into testing the following N lines too. Opt-in per check, because a wide window
      // can suppress a genuine finding that happens to sit near a sanitiser call.
      if (notMatchRe) {
        var mitigationText = lineText;
        var win = det.not_match_window || 0;
        if (win > 0) {
          var endIdx = loc.lineStart;
          for (var w = 0; w <= win; w++) {
            var nl = content.indexOf('\n', endIdx);
            if (nl === -1) { endIdx = content.length; break; }
            endIdx = nl + 1;
          }
          mitigationText = content.slice(loc.lineStart, endIdx);
        }
        if (notMatchRe.test(mitigationText)) continue;
      }
      if (det.skip_if_placeholder && isPlaceholder(m[0], catalog.placeholder_pattern)) continue;

      // Distinct occurrences drive the score; identical repeated lines do not. The same
      // `curl … | bash` copy-pasted into 13 CI jobs is one problem to fix, not thirteen.
      // Every occurrence is still reported — only the scored count is deduplicated.
      var dedupeKey = trim200(lineText).replace(/\s+/g, ' ').trim();
      if (!out.seen) out.seen = {};
      if (!Object.prototype.hasOwnProperty.call(out.seen, dedupeKey)) {
        out.seen[dedupeKey] = true;
        out.distinct = (out.distinct || 0) + 1;
      }

      out.total++;
      if (out.findings.length < 20) {
        out.findings.push({
          path: path,
          line: loc.line,
          column: loc.col,
          snippet: trim200(lineText),
          match: trimMatch(m[0]),
          url: permalink(target, sha, path, loc.line)
        });
      }
    }
    return { invalid: false };
  }

  function evaluateCheck(check, ctx) {
    var det = check.detector;
    var catalog = ctx.catalog;
    var hitCap = (det.hit_cap != null) ? det.hit_cap : catalog.scoring.default_hit_cap;

    // applies_if precondition, checked against the FULL tree (existence only).
    // It lives on the check, alongside `detector` — not inside it. Reading it from the
    // detector silently disabled every precondition, which failed repos for missing a
    // lockfile when they had no dependency manifest at all.
    var appliesIf = check.applies_if || det.applies_if;
    if (appliesIf && appliesIf.any_path) {
      if (!pathsExistInTree(ctx.allPaths, appliesIf.any_path)) {
        return { status: 'not_applicable', reason: appliesIfReason(check.id, appliesIf.any_path), findings: [], totalFindings: 0, deduction: 0 };
      }
    }

    if (det.kind === 'path_forbidden') {
      var forbidden = ctx.allPaths.filter(function (p) {
        return matchesAny(p, det.paths) && !(det.exclude && matchesAny(p, det.exclude));
      });
      if (forbidden.length === 0) {
        return { status: 'pass', findings: [], totalFindings: 0, deduction: 0 };
      }
      var capped = forbidden.slice(0, Math.max(hitCap, 20));
      var findings = capped.slice(0, 20).map(function (p) {
        return { path: p, line: 1, column: 1, snippet: p, match: p, url: permalink(ctx.target, ctx.sha, p, 1) };
      });
      var hits = Math.min(forbidden.length, hitCap);
      var deduction = catalog.scoring.per_hit[check.severity] * hits;
      return { status: 'fail', findings: findings, totalFindings: forbidden.length, deduction: deduction, findingsTruncated: forbidden.length > findings.length };
    }

    if (det.kind === 'path_required') {
      var found = pathsExistInTree(ctx.allPaths, det.paths);
      if (found) return { status: 'pass', findings: [], totalFindings: 0, deduction: 0 };
      var d = catalog.scoring.per_hit[check.severity] * 1;
      return { status: 'fail', findings: [], totalFindings: 0, deduction: d, reason: pathRequiredReason(check.id, det.paths) };
    }

    if (det.kind === 'meta' && det.handler === 'has_license') {
      var hasLicenseMeta = !!(ctx.repoMeta && ctx.repoMeta.license && ctx.repoMeta.license.key);
      var hasLicenseFile = pathsExistInTree(ctx.allPaths, ['LICENSE', 'LICENSE.*', 'LICENCE', 'LICENCE.*', 'COPYING', 'COPYING.*', '.github/LICENSE', '.github/LICENSE.*']);
      if (hasLicenseMeta || hasLicenseFile) return { status: 'pass', findings: [], totalFindings: 0, deduction: 0 };
      var dl = catalog.scoring.per_hit[check.severity] * 1;
      return { status: 'fail', findings: [], totalFindings: 0, deduction: dl, reason: 'No LICENSE file and no license declared in repository metadata' };
    }

    if (det.kind === 'content' || det.kind === 'content_required') {
      var wanted = filterFilesForCheck(check, ctx.eligiblePaths, catalog);
      var fetchedWanted = wanted.filter(function (p) { return Object.prototype.hasOwnProperty.call(ctx.files, p); });
      var skippedWanted = wanted.length - fetchedWanted.length;

      var out = { total: 0, findings: [] };
      var anyInvalid = false;
      for (var i = 0; i < fetchedWanted.length; i++) {
        var p = fetchedWanted[i];
        var fileRec = ctx.fileCache[p];
        if (!fileRec) {
          var content = ctx.files[p];
          fileRec = { content: content, lineStarts: buildLineStarts(content) };
          ctx.fileCache[p] = fileRec;
        }
        var r = scanFileForPattern(check, catalog, p, fileRec.content, fileRec.lineStarts, ctx.target, ctx.sha, out);
        if (r.invalid) anyInvalid = true;
      }

      if (anyInvalid) {
        return { status: 'skipped', reason: 'Detector pattern failed to compile at evaluation time.', findings: [], totalFindings: 0, deduction: 0 };
      }

      if (out.total > 0) {
        var hits2 = Math.min(out.distinct || out.total, hitCap);
        var deduction2 = catalog.scoring.per_hit[check.severity] * hits2;
        return { status: 'fail', findings: out.findings, totalFindings: out.total, deduction: deduction2, findingsTruncated: out.total > out.findings.length };
      }

      // Partial coverage. The correct conclusion depends on what the check is proving.
      //
      //   `content`          looks for something bad. Reading part of the tree and finding
      //                      nothing is a real (if incomplete) result — report pass, and
      //                      disclose the coverage rather than discarding the evaluation.
      //   `content_required` proves something good is present. Absence across a partial
      //                      read proves nothing, so it stays skipped.
      //
      // Either way, evaluating zero files is not a result at all.
      if (skippedWanted > 0) {
        if (fetchedWanted.length === 0) {
          return {
            status: 'skipped',
            reason: 'None of the ' + wanted.length + ' candidate file(s) could be read (file/time budget or fetch error).',
            findings: [], totalFindings: 0, deduction: 0
          };
        }
        if (det.kind === 'content_required') {
          return {
            status: 'skipped',
            reason: 'Only ' + fetchedWanted.length + ' of ' + wanted.length + ' candidate file(s) were read, so absence cannot be confirmed.',
            findings: [], totalFindings: 0, deduction: 0
          };
        }
        return {
          status: 'pass',
          partial: true,
          reason: 'No matches in the ' + fetchedWanted.length + ' of ' + wanted.length + ' candidate file(s) read within the scan budget.',
          findings: [], totalFindings: 0, deduction: 0
        };
      }

      if (det.kind === 'content_required' && wanted.length === 0) {
        // No candidate files matched at all (and no applies_if guarded this) — treat as not_applicable.
        return { status: 'not_applicable', reason: 'No files matching the required paths were found in the repository.', findings: [], totalFindings: 0, deduction: 0 };
      }

      if (det.kind === 'content_required') {
        return { status: 'fail', findings: [], totalFindings: 0, deduction: catalog.scoring.per_hit[check.severity] * 1, reason: det.fail_message || 'Required content was not found.' };
      }

      return { status: 'pass', findings: [], totalFindings: 0, deduction: 0 };
    }

    return { status: 'skipped', reason: 'Unknown detector kind.', findings: [], totalFindings: 0, deduction: 0 };
  }

  function grade(score) {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  }

  function evaluate(catalog, acquired, target, onProgress) {
    var ctx = {
      catalog: catalog,
      allPaths: acquired.allPaths,
      eligiblePaths: acquired.eligiblePaths,
      files: acquired.files,
      fileCache: Object.create(null),
      repoMeta: acquired.repoMeta,
      target: target,
      sha: acquired.sha
    };

    var byAgent = {};
    catalog.agents.forEach(function (a) { byAgent[a.id] = { agent: a, checks: [] }; });

    var checksByAgent = {};
    catalog.checks.forEach(function (ch) {
      (checksByAgent[ch.agent] = checksByAgent[ch.agent] || []).push(ch);
    });

    var counts = { critical: 0, high: 0, medium: 0, low: 0, pass: 0, fail: 0, not_applicable: 0, skipped: 0, total: catalog.checks.length };
    var totalAgentCount = catalog.agents.length;
    var agentsDone = 0;

    catalog.agents.forEach(function (agentDef) {
      var agentId = agentDef.id;
      onProgress({ phase: 'evaluating', agentId: agentId, pct: 70 + Math.round((agentsDone / totalAgentCount) * 25), message: 'Evaluating ' + agentDef.name + '…' });

      var checks = checksByAgent[agentId] || [];
      var deductionSum = 0;
      var checkResults = checks.map(function (ch) {
        var res = evaluateCheck(ch, ctx);
        counts[res.status]++;
        if (res.status === 'fail') {
          counts[ch.severity] = (counts[ch.severity] || 0) + 1;
          deductionSum += res.deduction;
        }
        var entry = {
          id: ch.id, name: ch.name, severity: ch.severity, status: res.status,
          cwe: ch.cwe, summary: ch.summary, risk: ch.risk, remediation: ch.remediation,
          deduction: Math.round(res.deduction * 100) / 100,
          findings: res.findings || [],
          findingsTruncated: !!res.findingsTruncated,
          totalFindings: res.totalFindings || 0
        };
        if (ch.fix) entry.fix = ch.fix;
        if (res.status !== 'fail' && res.reason) entry.reason = res.reason;
        if (res.status === 'fail' && res.reason) entry.reason = res.reason;
        return entry;
      });

      var agentScore = Math.max(0, agentDef.weight - deductionSum);
      byAgent[agentId].checks = checkResults;
      byAgent[agentId].score = Math.round(agentScore * 100) / 100;
      agentsDone++;
      onProgress({ phase: 'evaluating', agentId: agentId, pct: 70 + Math.round((agentsDone / totalAgentCount) * 25), message: agentDef.name + ' complete.' });
    });

    var agents = catalog.agents.map(function (a) {
      return {
        id: a.id, name: a.name, domain: a.domain, weight: a.weight,
        score: byAgent[a.id].score, checks: byAgent[a.id].checks
      };
    });

    var totalScore = agents.reduce(function (s, a) { return s + a.score; }, 0);
    totalScore = Math.round(totalScore * 10) / 10;

    return { agents: agents, counts: counts, score: totalScore, grade: grade(totalScore) };
  }

  // ---------------------------------------------------------------------
  // Main scan()
  // ---------------------------------------------------------------------
  function scan(target, opts) {
    opts = opts || {};
    var onProgress = opts.onProgress || function () {};
    var source = opts.source || 'web';

    if (!target || target.kind !== 'github') {
      if (target && target.kind === 'website') {
        return Promise.reject(ScanError('UNSUPPORTED_TARGET', 'Browsers cannot fetch arbitrary web origins (CORS). Use the CLI: python3 examine.py "' + target.url + '"'));
      }
      if (target && target.kind === 'package') {
        return Promise.reject(ScanError('UNSUPPORTED_TARGET', 'Package identifiers are not directly scannable. Use the CLI: python3 examine.py <path-to-checkout>'));
      }
      return Promise.reject(ScanError('UNSUPPORTED_TARGET', 'Could not understand the scan target. Provide a GitHub URL or owner/repo.'));
    }

    var catalog = global.CERBERUS_CHECKS;
    if (!catalog) {
      return Promise.reject(ScanError('NETWORK', 'Check catalog (assets/checks.js) was not loaded.'));
    }
    opts.catalog = catalog;

    return acquireRepo(target, opts, onProgress).then(function (acquired) {
      onProgress({ phase: 'evaluating', pct: 70, message: 'Evaluating checks…' });
      var evalResult = evaluate(catalog, acquired, target, onProgress);

      onProgress({ phase: 'scoring', pct: 97, message: 'Scoring…' });

      var notes = acquired.notes.slice();
      if (acquired.rateLimit && acquired.rateLimit.remaining !== null && acquired.rateLimit.remaining < 5) {
        notes.push('GitHub API rate limit is low (' + acquired.rateLimit.remaining + ' requests remaining, resets ' + acquired.rateLimit.resetAt + ').');
      }

      var report = {
        schema: 'cerberus.report/2',
        target: {
          kind: 'github',
          display: target.owner + '/' + target.repo,
          url: 'https://github.com/' + target.owner + '/' + target.repo,
          owner: target.owner,
          repo: target.repo,
          ref: acquired.ref,
          sha: acquired.sha
        },
        scannedAt: new Date().toISOString(),
        engine: { version: ENGINE_VERSION, checksVersion: catalog.version, source: source },
        score: evalResult.score,
        grade: evalResult.grade,
        counts: evalResult.counts,
        repo: {
          description: acquired.repoMeta.description || '',
          stars: acquired.repoMeta.stargazers_count || 0,
          license: (acquired.repoMeta.license && acquired.repoMeta.license.spdx_id) || null,
          archived: !!acquired.repoMeta.archived,
          pushedAt: acquired.repoMeta.pushed_at,
          primaryLanguage: acquired.repoMeta.language || null
        },
        coverage: acquired.coverage,
        agents: evalResult.agents,
        notes: notes
      };

      onProgress({ phase: 'done', pct: 100, message: 'Scan complete.' });
      return report;
    });
  }

  global.CerberusScanner = {
    parseTarget: parseTarget,
    scan: scan,
    _internal: { globMatch: globMatch, globToRegExp: globToRegExp, isPlaceholder: isPlaceholder } // exposed for testing only
  };
})(typeof window !== 'undefined' ? window : this);
