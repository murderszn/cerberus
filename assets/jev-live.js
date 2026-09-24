/* Real NDJSON events only. Keys and source never enter this visualization. */
(function () {
    'use strict';
    var nativeScan = window.CerberusScanner && window.CerberusScanner.scan;
    if (!nativeScan) return;
    var local = /^(127\.0\.0\.1|localhost)$/.test(location.hostname) && location.port === '8765';
    var consent = document.createElement('label');
    consent.className = 'jev-consent';
    var checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.disabled = !local;
    var label = document.createElement('span');
    var title = document.createElement('strong');
    title.textContent = 'Jev · Live file intelligence';
    var description = document.createElement('small');
    description.textContent = local ? 'Watch files become a review queue. Opt in to send eligible, redacted source to TypeSafe. Up to 100 files; API charges may apply.' : 'Live Jev is available in the local preview. A secure production bridge is not configured yet.';
    label.append(title, description);
    consent.append(checkbox, label);
    var anchor = document.querySelector('#view-splash .chips') || document.querySelector('.chips');
    if (anchor) anchor.before(consent);

    var panel = document.createElement('section');
    panel.className = 'jev-live';
    panel.hidden = true;
    panel.setAttribute('aria-label', 'Jev live file categorization');
    // Only static markup is used here. All remote values use textContent.
    panel.innerHTML = '<div class="jev-top"><span class="jev-eyebrow">JEV / FILE INTELLIGENCE</span><span class="jev-status" role="status" aria-live="polite">Standby</span></div>' +
        '<h3>File intelligence.</h3><p class="jev-caption">Live categorization, measured response times, and a clear order for review.</p>' +
        '<div class="jev-metrics"><div class="jev-metric"><strong data-metric="files">0</strong><span>files categorized</span></div><div class="jev-metric"><strong data-metric="latency">—</strong><span>median Jev response · ms</span></div><div class="jev-metric"><strong data-metric="time">0.0s</strong><span>total triage time</span></div></div>' +
        '<div class="jev-flow"><div><div class="jev-label">01 / Source map <span class="jev-total"></span></div><div class="jev-grid" aria-label="File states"></div><div class="jev-legend">Outlined: queued · Inset square: evaluating<br>Dark → light: high → low review priority.<br>Select a file to inspect its category probabilities.</div></div><div class="jev-connector" aria-hidden="true">→</div><div><div class="jev-label">02 / Review priority</div>' +
        ['high', 'medium', 'low'].map(function (p) { return '<div class="jev-lane" data-priority="' + p + '"><div class="jev-lane-head"><span>' + p[0].toUpperCase() + p.slice(1) + '</span><strong>0</strong></div><div class="jev-track"><span></span></div><span class="jev-lane-note">' + ({high:'≥ 70% concern probability',medium:'40–69% concern probability',low:'< 40% · not a safety guarantee'}[p]) + '</span></div>'; }).join('') + '</div></div>' +
        '<div class="jev-detail"><div class="jev-label">03 / <span class="jev-detail-label">Awaiting first decision</span></div><div class="jev-path">Repository content stays out of this display.</div><div class="jev-probabilities"></div></div>' +
        '<div class="jev-footer"><span class="jev-coverage">No files assessed</span><span>Advisory · not confirmed findings</span></div><p class="jev-error" role="status"></p><button type="button" class="jev-open" hidden>Open security report →</button>';
    var $ = function (selector) { return panel.querySelector(selector); };
    var counts, tiles, records, latencies, analyzed, skipped, started, timer, selected, reportKey;
    function mount() {
        var dock = document.getElementById('workspace-scan-jev');
        if (dock) { dock.append(panel); return; }
        var scan = document.getElementById('view-scan');
        var loader = document.getElementById('pack-loader');
        scan.insertBefore(panel, loader || scan.firstChild);
    }
    function reset() {
        mount(); panel.hidden = false; panel.dataset.state = 'waiting';
        counts = {high:0, medium:0, low:0}; tiles = new Map(); records = new Map();
        latencies = []; analyzed = 0; skipped = 0; selected = null;
        $('.jev-grid').replaceChildren(); $('.jev-probabilities').replaceChildren();
        $('.jev-status').textContent = 'Waiting for source revision';
        $('.jev-path').textContent = 'Native checks run first. Jev then assesses this exact commit.';
        $('.jev-detail-label').textContent = 'Awaiting first decision';
        $('.jev-error').textContent = ''; $('.jev-total').textContent = '';
        $('[data-metric="time"]').textContent = '0.0s';
        $('.jev-open').hidden = true;
        update();
    }
    function update() {
        $('[data-metric="files"]').textContent = String(analyzed);
        var sorted = latencies.slice().sort(function(a,b) { return a-b; });
        var middle = Math.floor(sorted.length / 2);
        var median = sorted.length % 2 ? sorted[middle] : (sorted[middle-1] + sorted[middle]) / 2;
        $('[data-metric="latency"]').textContent = sorted.length ? Math.round(median).toLocaleString() : '—';
        Object.keys(counts).forEach(function (priority) {
            var lane = $('[data-priority="' + priority + '"]');
            lane.querySelector('strong').textContent = String(counts[priority]);
            lane.querySelector('.jev-track span').style.width = (analyzed ? counts[priority] / analyzed * 100 : 0) + '%';
        });
        $('.jev-coverage').textContent = analyzed + ' assessed / ' + skipped + ' unassessed';
    }
    function detail(file) {
        $('.jev-detail-label').textContent = file.priority ? file.priority + ' review priority' : 'Unassessed';
        $('.jev-path').textContent = file.path;
        $('.jev-probabilities').replaceChildren();
        (file.potentialRisks || []).forEach(function(risk) {
            var row = document.createElement('div'); row.className = 'jev-probability';
            var name = document.createElement('span'); name.textContent = risk.category;
            var value = document.createElement('strong'); value.textContent = (risk.probability * 100).toFixed(1) + '%';
            row.append(name, value); $('.jev-probabilities').append(row);
        });
        if (file.reason) $('.jev-detail-label').textContent = 'Unassessed / ' + file.reason.replaceAll('_', ' ');
    }
    function event(evt) {
        if (evt.type === 'phase') $('.jev-status').textContent = evt.message;
        if (evt.type === 'inventory') {
            $('.jev-total').textContent = '/ ' + evt.candidates.length + ' eligible';
            evt.candidates.forEach(function(path) {
                var tile = document.createElement('button'); tile.type = 'button'; tile.className = 'jev-tile';
                tile.dataset.state = 'queued'; tile.setAttribute('aria-label', path + ': queued');
                tile.title = path + ': queued';
                tile.addEventListener('click', function() {
                    selected = selected === path ? null : path;
                    tiles.forEach(function(button, name) { button.setAttribute('aria-pressed', String(name === selected)); });
                    if (records.has(path)) detail(records.get(path));
                    else { $('.jev-path').textContent = path; $('.jev-detail-label').textContent = tile.dataset.state; $('.jev-probabilities').replaceChildren(); }
                });
                tiles.set(path, tile); $('.jev-grid').append(tile);
            });
        }
        if (evt.type === 'evaluating') {
            $('.jev-status').textContent = 'Evaluating';
            var tile = tiles.get(evt.path);
            if (tile) { tile.dataset.state = 'active'; tile.setAttribute('aria-label', evt.path + ': evaluating'); }
            if (!selected) { $('.jev-path').textContent = evt.path; $('.jev-detail-label').textContent = 'Evaluating'; }
        }
        if (evt.type === 'categorized' || evt.type === 'skipped') {
            var file = evt.file; records.set(file.path, file);
            var mark = tiles.get(file.path);
            if (mark) { mark.dataset.state = file.priority || 'skipped'; mark.title = file.path + ': ' + (file.priority || 'unassessed'); mark.setAttribute('aria-label', mark.title); }
            if (evt.type === 'categorized') { analyzed++; counts[file.priority]++; latencies.push(evt.latencyMs); }
            else skipped++;
            if ((!selected && evt.type === 'categorized') || selected === file.path) detail(file);
            update();
        }
    }
    async function run(report, opts) {
        reportKey = '#/report/' + encodeURIComponent(report.target.owner) + '/' + encodeURIComponent(report.target.repo);
        started = performance.now(); panel.dataset.state = 'running';
        timer = setInterval(function() { $('[data-metric="time"]').textContent = ((performance.now()-started)/1000).toFixed(1) + 's'; }, 100);
        var completed = false;
        try {
            var response = await fetch('http://127.0.0.1:8766/triage', {
                method:'POST', headers:{'Content-Type':'application/json'}, signal:opts.signal,
                body:JSON.stringify({repo_url:'https://github.com/' + report.target.owner + '/' + report.target.repo, sha:report.target.sha, githubToken:opts.token || ''})
            });
            if (!response.ok) throw new Error(response.status === 409 ? 'Another Jev scan is active. Native results are ready.' : 'The local Jev bridge rejected the request.');
            var reader = response.body.getReader(), decoder = new TextDecoder(), buffer = '';
            while (true) {
                var chunk = await reader.read();
                if (chunk.done) break;
                buffer += decoder.decode(chunk.value, {stream:true});
                var newline;
                while ((newline = buffer.indexOf('\n')) >= 0) {
                    var line = buffer.slice(0,newline); buffer = buffer.slice(newline+1);
                    if (!line.trim()) continue;
                    var evt = JSON.parse(line);
                    if (evt.type === 'error') throw new Error(evt.message);
                    if (evt.type === 'done') { report.triage = evt.triage; completed = true; }
                    else event(evt);
                }
            }
            if (!completed) throw new Error('The stream ended early. Partial decisions are not a complete assessment.');
            report.triage.telemetry = {latenciesMs:latencies.slice(), elapsedMs:Math.round(performance.now()-started)};
            $('.jev-status').textContent = 'Categorization complete';
            panel.dataset.state = 'complete';
        } catch (err) {
            if (opts.signal && opts.signal.aborted) throw err;
            panel.dataset.state = 'error'; $('.jev-status').textContent = 'Triage incomplete';
            $('.jev-error').textContent = err instanceof TypeError ? 'Start the local bridge: python3 -m servers.jev_live. Your native report is still available.' : err.message;
        } finally { clearInterval(timer); }
        await new Promise(function(resolve, reject) {
            var button = $('.jev-open'); button.hidden = false;
            function abort() { cleanup(); reject(new DOMException('Scan canceled','AbortError')); }
            function cleanup() { button.onclick = null; if (opts.signal) opts.signal.removeEventListener('abort',abort); }
            button.onclick = function() { cleanup(); button.hidden = true; resolve(); };
            if (opts.signal) { if (opts.signal.aborted) abort(); else opts.signal.addEventListener('abort',abort,{once:true}); }
        });
        return report;
    }
    window.CerberusScanner.scan = async function(target, opts) {
        opts = opts || {};
        if (!checkbox.checked || !local) { panel.hidden = true; return nativeScan.call(this,target,opts); }
        reset();
        try { return await run(await nativeScan.call(this,target,opts),opts); }
        catch(err) { clearInterval(timer); panel.dataset.state = 'error'; throw err; }
    };
    // Keep the completed instrument available alongside the report, without replaying it.
    var reportView = document.getElementById('view-report');
    window.addEventListener('cerberus:report', function(e) {
        var report = e.detail;
        if (!report || !report.triage || report.triage.source !== 'jev') { panel.hidden = true; return; }
        var key = '#/report/' + encodeURIComponent(report.target.owner) + '/' + encodeURIComponent(report.target.repo);
        if (key !== reportKey || panel.dataset.state !== 'complete') {
            reset(); reportKey = key;
            var files = report.triage.files || [];
            event({type:'inventory', candidates:files.filter(function(f) { return f.status === 'analyzed'; }).map(function(f) { return f.path; })});
            files.forEach(function(file) { event({type:file.status === 'analyzed' ? 'categorized' : 'skipped', file:file, latencyMs:0}); });
            latencies = report.triage.telemetry ? report.triage.telemetry.latenciesMs : [];
            update();
            $('[data-metric="time"]').textContent = report.triage.telemetry ? (report.triage.telemetry.elapsedMs/1000).toFixed(1)+'s' : '—';
            panel.dataset.state = 'complete'; $('.jev-status').textContent = 'Recorded categorization';
        }
        panel.hidden = false;
        if (reportView) (document.getElementById('workspace-report-jev') || reportView).prepend(panel);
    });
    if (reportView) new MutationObserver(function() {
        if (!reportView.hidden && !panel.hidden && panel.dataset.state === 'complete') {
            if (location.hash.toLowerCase() === reportKey.toLowerCase()) (document.getElementById('workspace-report-jev') || reportView).prepend(panel);
            else panel.hidden = true;
        }
    }).observe(reportView,{attributes:true,attributeFilter:['hidden']});
})();
