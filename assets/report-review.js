/* Report-derived review notes. No model calls, invented execution traces, or score projections. */
(function (root) {
  'use strict';
  var severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  function list(value) { return Array.isArray(value) ? value : []; }
  function number(value) { return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null; }
  function text(value) { return value == null ? '' : String(value); }
  function plural(n, word) { return n + ' ' + word + (n === 1 ? '' : 's'); }
  function escape(value) { return text(value).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function sourceUrl(target, finding) {
    if (!target.owner || !target.repo || !target.sha || !finding.path) return '';
    var url = 'https://github.com/' + [target.owner, target.repo, 'blob', target.sha].map(encodeURIComponent).join('/') + '/' + text(finding.path).split('/').map(encodeURIComponent).join('/');
    return url + (number(finding.line) && Number.isInteger(finding.line) ? '#L' + finding.line : '');
  }
  function build(report) {
    report = report || {};
    var target = report.target || {}, coverage = report.coverage || {}, repo = report.repo || {};
    var counts = { pass: 0, fail: 0, skipped: 0, not_applicable: 0, unknown: 0, total: 0 };
    var failures = [], unevaluated = [], observations = [], files = new Set();
    var agents = list(report.agents);
    agents.forEach(function (agent) {
      var results = list(agent.checks), failed = [], passed = 0, skipped = 0, na = 0;
      results.forEach(function (check) {
        counts.total++;
        if (Object.prototype.hasOwnProperty.call(counts, check.status) && check.status !== 'total') counts[check.status]++;
        else counts.unknown++;
        if (check.status === 'pass') passed++;
        else if (check.status === 'skipped') skipped++;
        else if (check.status === 'not_applicable') na++;
        if (check.status === 'skipped' || check.status === 'not_applicable') {
          unevaluated.push({ id: text(check.id), name: text(check.name), status: check.status, reason: text(check.reason) || 'No evaluation reason recorded.' });
        }
        if (check.status !== 'fail') return;
        var evidence = list(check.findings).map(function (finding) {
          if (finding.path) files.add(text(finding.path));
          return { path: text(finding.path), line: number(finding.line), url: sourceUrl(target, finding) };
        });
        var item = {
          id: text(check.id), name: text(check.name), agent: text(agent.name), domain: text(agent.domain),
          severity: Object.prototype.hasOwnProperty.call(severityOrder, check.severity) ? check.severity : 'unrated',
          deduction: number(check.deduction) || 0,
          findingCount: Math.max(number(check.totalFindings) || 0, evidence.length),
          evidence: evidence, truncated: !!check.findingsTruncated || (number(check.totalFindings) || 0) > evidence.length,
          observation: text(check.reason || check.summary) || 'This check returned a failed result.',
          risk: text(check.risk), action: text(check.remediation) || 'Inspect this check and its evidence, confirm the intended behavior, and define a targeted fix.',
          cwe: text(check.cwe)
        };
        failures.push(item); failed.push(item);
      });
      var unknown = results.length - passed - failed.length - skipped - na;
      var note = failed.length ? plural(failed.length, 'failed check') + ': ' + failed.map(function (c) { return c.name + ' (' + c.id + ')'; }).join('; ') + '.'
        : passed ? plural(passed, 'evaluated check') + ' passed in ' + text(agent.domain || agent.name) + '. No failed check was recorded in the evaluated scope.'
        : 'No pass/fail result was recorded for this domain.';
      if (skipped || na || unknown) note += ' ' + [skipped ? plural(skipped, 'check') + ' skipped' : '', na ? na + ' not applicable' : '', unknown ? unknown + ' with unknown status' : ''].filter(Boolean).join('; ') + '.';
      observations.push({ name: text(agent.name), domain: text(agent.domain), passed: passed, failed: failed.length, skipped: skipped, notApplicable: na, note: note });
    });
    failures.sort(function (a, b) { return (severityOrder[a.severity] ?? 4) - (severityOrder[b.severity] ?? 4) || b.deduction - a.deduction || a.id.localeCompare(b.id); });
    observations.sort(function (a, b) { return b.failed - a.failed || a.name.localeCompare(b.name); });
    var evaluated = counts.pass + counts.fail;
    var affected = observations.filter(function (a) { return a.failed; }).length;
    var scanned = number(coverage.filesScanned), eligible = number(coverage.filesEligible), tree = number(coverage.filesInTree), skippedFiles = number(coverage.filesSkipped);
    var coverageText = scanned === null ? 'File coverage was not recorded.' : plural(scanned, 'file') + ' read' + (eligible !== null ? ' out of ' + eligible + ' eligible' : '') + (tree !== null ? '; ' + tree + ' in the repository tree' : '') + '.';
    var headline = counts.fail ? plural(counts.fail, 'failed check') + ' to review.' : evaluated ? 'No failed checks in the evaluated scope.' : 'No evaluated checks were recorded.';
    var summary = counts.fail
      ? plural(counts.fail, 'failed check') + ' across ' + affected + ' of ' + agents.length + ' agent domains. ' + plural(counts.pass, 'check') + ' passed.'
      : plural(counts.pass, 'check') + ' passed across ' + agents.length + ' recorded agent domains.';
    if (counts.skipped || counts.unknown) summary += ' ' + plural(counts.skipped + counts.unknown, 'check') + ' still need evaluation.';
    var learnings = [];
    if (repo.primaryLanguage) learnings.push('GitHub identifies ' + text(repo.primaryLanguage) + ' as the primary language. This is repository metadata, not a complete inventory of the stack.');
    if (failures.length) {
      var levels = {};
      failures.forEach(function (f) { levels[f.severity] = (levels[f.severity] || 0) + 1; });
      learnings.push('Recorded failures by severity: ' + Object.keys(levels).map(function (key) { return levels[key] + ' ' + key; }).join(', ') + '. Priority follows catalog severity, then score deduction; exploitability was not tested.');
      learnings.push(files.size ? plural(files.size, 'distinct file') + ' named in the failure evidence. Missing-file and configuration checks may have no line-level location.' : 'The failed checks have no file-level evidence attached. Review their recorded conditions before choosing files to change.');
    }
    var clean = observations.filter(function (a) { return a.passed && !a.failed; });
    if (clean.length) learnings.push('No failed evaluated checks in: ' + clean.map(function (a) { return a.name; }).join(', ') + '. These are results for the recorded checks, not proof of complete security.');
    if (repo.archived) learnings.push('GitHub marks this repository as archived. Confirm the maintenance owner before planning changes.');
    if (!learnings.length) learnings.push('The report does not contain enough evaluated results to infer repository-specific patterns.');
    var assumptions = [
      target.sha ? 'This review applies to commit ' + text(target.sha).slice(0, 12) + (target.ref ? ' on ' + text(target.ref) : '') + '. Later changes require a new scan.' : 'No commit SHA was recorded. Confirm which revision these results describe.',
      'The browser scanner examines repository files and metadata. It does not execute the application, prove exploitability, or verify deployed infrastructure.',
      'No fix was applied or tested by this scan. Remediation and any patch examples require review and validation in the target project.'
    ];
    if (coverage.truncated) assumptions.push('Coverage is incomplete: the report marks the file tree or acquisition as truncated. The score does not account for unread code.');
    if (scanned === null || eligible === null) assumptions.push('Coverage counts are missing; do not assume that all eligible files were read.');
    else if (scanned < eligible) assumptions.push((eligible - scanned) + ' eligible files were not read. Re-run with sufficient access and acquisition budget before treating absence checks as conclusive.');
    if (skippedFiles) assumptions.push(plural(skippedFiles, 'file') + ' skipped during acquisition' + (Object.keys(coverage.skipReasons || {}).length ? ': ' + Object.entries(coverage.skipReasons).map(function (pair) { return text(pair[0]).replace(/_/g, ' ') + ' (' + text(pair[1]) + ')'; }).join(', ') : '') + '.');
    if (counts.skipped) assumptions.push(plural(counts.skipped, 'check') + ' skipped. The reasons below are unresolved gaps, not passing results.');
    if (counts.not_applicable) assumptions.push(plural(counts.not_applicable, 'check') + ' marked not applicable because their conditions were not met in the available repository data.');
    if (counts.unknown) assumptions.push(plural(counts.unknown, 'check') + ' have no recognized outcome and are excluded from pass/fail conclusions.');
    if (failures.some(function (f) { return f.truncated; })) assumptions.push('Some checks include only a subset of their finding locations. Counts may exceed the evidence shown.');
    var notes = list(report.notes).map(text).filter(Boolean);
    var steps = failures.map(function (f, i) {
      return { number: i + 1, title: f.name, status: f.severity, detail: f.action, why: f.observation, risk: f.risk, checkId: f.id, agent: f.agent, evidence: f.evidence, findingCount: f.findingCount, truncated: f.truncated };
    });
    if (coverage.truncated || (scanned !== null && eligible !== null && scanned < eligible) || counts.skipped || counts.unknown || !evaluated) {
      steps.push({ number: steps.length + 1, title: 'Close the coverage gaps', status: 'follow-up', detail: 'Review skipped files and check reasons below. Resolve access, size, or time limits and run the scan again.', why: coverageText, evidence: [] });
    }
    if (!failures.length && evaluated) steps.push({ number: steps.length + 1, title: 'Validate beyond the static checks', status: 'follow-up', detail: 'Confirm runtime permissions, deployment settings, and project tests. Keep this commit and report as a baseline for the next change.', why: 'No failed check was recorded; the scan does not test runtime behavior.', evidence: [] });
    if (failures.length) steps.push({ number: steps.length + 1, title: 'Verify the changes', status: 'follow-up', detail: 'Review each proposed change, run the project’s relevant tests, and re-run Cerberus. Compare the new results with this commit before merging.', why: 'A lower failure count must be observed in a subsequent scan; no score improvement is assumed here.', evidence: [] });
    return { target: text(target.display || [target.owner, target.repo].filter(Boolean).join('/') || 'Repository'), sha: text(target.sha), ref: text(target.ref), scannedAt: text(report.scannedAt), score: number(report.score), grade: text(report.grade), headline: headline, summary: summary, coverageText: coverageText, filesScanned: scanned, evaluated: evaluated, counts: counts, agents: observations, failures: failures, learnings: learnings, assumptions: assumptions, notes: notes, unevaluated: unevaluated, steps: steps };
  }
  function locationHtml(finding) {
    var label = finding.path + (finding.line ? ':' + finding.line : '');
    if (!label) return '';
    return finding.url ? '<a href="' + escape(finding.url) + '" target="_blank" rel="noopener noreferrer">' + escape(label) + '</a>' : '<span>' + escape(label) + '</span>';
  }
  function bullets(items) { return '<ul class="review-list">' + items.map(function (item) { return '<li>' + escape(item) + '</li>'; }).join('') + '</ul>'; }
  function html(review, interactive) {
    var stats = [[review.evaluated, 'checks evaluated'], [review.counts.fail, 'failed checks'], [review.filesScanned === null ? '—' : review.filesScanned, 'files read'], [review.counts.skipped + review.counts.unknown, 'checks unresolved']];
    var stepHtml = review.steps.map(function (step) {
      var evidence = step.evidence.map(locationHtml).filter(Boolean);
      return '<article class="review-step"><span class="review-step-number">' + String(step.number).padStart(2, '0') + '</span><div class="review-step-content"><div class="review-step-heading"><h3>' + escape(step.title) + '</h3><span class="review-severity severity-' + escape(step.status) + '">' + escape(step.status) + '</span></div>' +
        (step.checkId ? '<p class="review-meta">' + escape(step.agent + ' / ' + step.checkId) + (step.findingCount ? ' · ' + escape(plural(step.findingCount, 'finding')) : ' · repository condition') + '</p>' : '') +
        '<p><strong>Observed.</strong> ' + escape(step.why) + '</p>' +
        (step.risk ? '<p class="review-risk"><strong>Why it matters.</strong> ' + escape(step.risk) + '</p>' : '') +
        '<p><strong>Next step.</strong> ' + escape(step.detail) + '</p>' +
        (evidence.length ? '<div class="review-evidence">' + evidence.slice(0, 3).join('') + '</div>' : '') +
        (evidence.length > 3 ? '<details class="review-more"><summary>' + (evidence.length - 3) + ' more recorded locations</summary><div class="review-evidence">' + evidence.slice(3).join('') + '</div></details>' : '') +
        (step.truncated ? '<p class="review-meta">The report contains a subset of finding locations.</p>' : '') +
        (interactive && step.checkId ? '<button type="button" class="review-check-link" data-review-check="' + escape(step.checkId) + '">Inspect check <span aria-hidden="true">→</span></button>' : '') + '</div></article>';
    }).join('');
    return '<section class="review-overview"><p class="review-kicker">Scan notes / ' + escape(review.target) + '</p><h2>' + escape(review.headline) + '</h2><p>' + escape(review.summary) + '</p><div class="review-stats">' + stats.map(function (s) { return '<div><b>' + escape(s[0]) + '</b><span>' + escape(s[1]) + '</span></div>'; }).join('') + '</div><p class="review-scope">' + escape(review.coverageText) + '</p></section>' +
      '<section class="review-section"><div class="review-section-heading"><span>01</span><h2>Findings &amp; next steps</h2></div><p class="review-caption">Prioritized from this report’s severity and score deductions.</p>' + stepHtml + '</section>' +
      '<section class="review-section"><div class="review-section-heading"><span>02</span><h2>What we learned</h2></div>' + bullets(review.learnings) +
      '<details class="review-agent-notes"><summary>Notes from all ' + review.agents.length + ' agent domains</summary><div class="review-agent-list">' + review.agents.map(function (agent) { return '<article><h3>' + escape(agent.name) + '<span>' + escape(agent.domain) + '</span></h3><p>' + escape(agent.note) + '</p></article>'; }).join('') + '</div></details></section>' +
      '<section class="review-section"><div class="review-section-heading"><span>03</span><h2>Assumptions &amp; open questions</h2></div>' + bullets(review.assumptions) +
      (review.unevaluated.length ? '<details class="review-agent-notes"><summary>Why ' + review.unevaluated.length + ' checks were skipped or not applicable</summary><ul class="review-list">' + review.unevaluated.map(function (c) { return '<li><strong>' + escape(c.id + ' · ' + c.name) + '</strong><span class="review-meta"> ' + escape(c.status.replace(/_/g, ' ')) + '</span><p>' + escape(c.reason) + '</p></li>'; }).join('') + '</ul></details>' : '') + '</section>' +
      (review.notes.length ? '<section class="review-section"><div class="review-section-heading"><span>04</span><h2>Scanner notes</h2></div>' + bullets(review.notes) + '</section>' : '');
  }
  function markdown(review) {
    var lines = ['## Scan notes — ' + review.target, '', review.headline, '', review.summary, '', review.coverageText, '', '### Findings & next steps', ''];
    review.steps.forEach(function (s) {
      lines.push(s.number + '. **' + s.title + '** [' + s.status + ']' + (s.checkId ? ' — ' + s.agent + ' / ' + s.checkId : ''), '   - Observed: ' + s.why);
      if (s.risk) lines.push('   - Why it matters: ' + s.risk);
      lines.push('   - Next step: ' + s.detail);
      s.evidence.forEach(function (f) { if (f.path) lines.push('   - Evidence: ' + f.path + (f.line ? ':' + f.line : '') + (f.url ? ' (' + f.url + ')' : '')); });
      if (s.truncated) lines.push('   - Finding locations are truncated in the report.');
    });
    [['What we learned', review.learnings], ['Agent observations', review.agents.map(function (a) { return a.name + ' / ' + a.domain + ': ' + a.note; })], ['Assumptions & open questions', review.assumptions], ['Unevaluated checks', review.unevaluated.map(function (c) { return c.id + ' [' + c.status + ']: ' + c.reason; })], ['Scanner notes', review.notes]].forEach(function (section) {
      if (section[1].length) lines.push('', '### ' + section[0], '', ...section[1].map(function (x) { return '- ' + x; }));
    });
    return lines.join('\n');
  }
  function standalone(report, css) {
    var review = build(report);
    var json = JSON.stringify(report).replace(/</g, '\\u003c');
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>Cerberus report — ' + escape(review.target) + '</title><style>' + (css || '') + '</style></head><body class="review-document"><header class="export-header"><p>CERBERUS LABS / SECURITY EXAMINATION</p><h1>' + escape(review.target) + '</h1><div class="export-score">' + escape(review.score === null ? '—' : review.score) + '<small>/100</small><span>' + escape(review.grade || '—') + '</span></div><p>' + escape(review.scannedAt || 'Scan date not recorded') + '<br>Commit ' + escape(review.sha || 'not recorded') + (review.ref ? ' · ' + escape(review.ref) : '') + '</p></header><main>' + html(review, false) + '</main><footer class="export-footer">Generated from the recorded Cerberus scan. Raw report data is embedded in this file.</footer><script id="cerberus-report-data" type="application/json">' + json + '</script></body></html>';
  }
  var api = { build: build, html: html, markdown: markdown, standalone: standalone };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CerberusReview = api;
})(typeof window !== 'undefined' ? window : globalThis);
