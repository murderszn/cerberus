import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const Review = require('../assets/report-review.js');
const sample = JSON.parse(fs.readFileSync(new URL('../assets/sample-scroll-world.json', import.meta.url)));
const clone = (x) => JSON.parse(JSON.stringify(x));

test('sample notes describe real counts and catalog conditions without mutating the report', () => {
  const before = JSON.stringify(sample);
  const r = Review.build(sample);
  assert.equal(r.counts.fail, 5);
  assert.equal(r.counts.pass, 48);
  assert.equal(r.counts.not_applicable, 6);
  assert.equal(r.evaluated, 53);
  assert.equal(r.filesScanned, 5);
  assert.equal(r.failures.length, 5);
  assert.equal(r.agents.length, 9);
  assert.match(r.coverageText, /5 files read out of 5 eligible; 11 in the repository tree/);
  assert.equal(JSON.stringify(sample), before);
});

test('priority follows severity before deduction and every action retains its recorded check', () => {
  const report = clone(sample);
  report.agents = [{name:'TEST',domain:'Test domain',checks:[
    {id:'LOW',name:'Low check',status:'fail',severity:'low',deduction:50,remediation:'Low action'},
    {id:'CRITICAL',name:'Critical check',status:'fail',severity:'critical',deduction:1,remediation:'Critical action'},
    {id:'HIGH',name:'High check',status:'fail',severity:'high',deduction:10,remediation:'High action'}
  ]}];
  const r = Review.build(report);
  assert.deepEqual(r.failures.map(x=>x.id), ['CRITICAL','HIGH','LOW']);
  assert.equal(r.steps[0].detail, 'Critical action');
  assert.notEqual(r.summary, Review.build(sample).summary);
});

test('a clean result never produces fake remediation or marks skipped checks as passing', () => {
  const report = clone(sample);
  for (const a of report.agents) for (const c of a.checks) if(c.status==='fail') {c.status='pass';c.findings=[];}
  report.agents[0].checks[0].status='skipped';
  report.agents[0].checks[0].reason='Candidate files could not be fetched.';
  const r=Review.build(report);
  assert.equal(r.failures.length,0);
  assert.equal(r.counts.skipped,1);
  assert.equal(r.evaluated,52);
  assert.match(r.summary,/still need evaluation/);
  assert.ok(r.steps.some(s=>s.title==='Close the coverage gaps'));
  assert.ok(r.steps.some(s=>s.title==='Validate beyond the static checks'));
  assert.ok(r.unevaluated.some(s=>s.reason==='Candidate files could not be fetched.'));
});

test('coverage gaps, missing metadata, truncation and unknown outcomes stay explicit', () => {
  const r=Review.build({score:100,agents:[{name:'ONLY',checks:[{id:'X',status:'mystery'}]}],coverage:{filesScanned:2,filesEligible:5,filesSkipped:3,truncated:true,skipReasons:{fetch_error:3}}});
  assert.equal(r.evaluated,0);
  assert.equal(r.counts.unknown,1);
  assert.match(r.headline,/No evaluated checks/);
  assert.ok(r.assumptions.some(s=>s.includes('3 eligible files were not read')));
  assert.ok(r.assumptions.some(s=>s.includes('fetch error (3)')));
  assert.ok(r.assumptions.some(s=>s.includes('truncated')));
  assert.ok(r.assumptions.some(s=>s.includes('No commit SHA')));
  assert.match(Review.build({}).coverageText,/not recorded/);
  assert.ok(Review.build({}).assumptions.some(s=>s.includes('Coverage counts are missing')));
});

test('missing-file failures retain their reason without inventing file or line evidence', () => {
  const r=Review.build({agents:[{name:'A',checks:[{id:'MISSING',name:'Policy missing',status:'fail',severity:'medium',reason:'No SECURITY.md found',findings:[],totalFindings:0}]}]});
  assert.equal(r.steps[0].why,'No SECURITY.md found');
  assert.equal(r.steps[0].evidence.length,0);
  assert.match(Review.html(r,true),/repository condition/);
});

test('source links are pinned to the report commit and reported totals survive truncated evidence', () => {
  const r=Review.build({target:{owner:'acme',repo:'repo',sha:'deadbeef'},agents:[{name:'A',checks:[{id:'X',status:'fail',severity:'high',totalFindings:7,findingsTruncated:true,findings:[{path:'src/a b.js',line:12,url:'javascript:alert(1)'}]}]}]});
  assert.equal(r.failures[0].findingCount,7);
  assert.equal(r.failures[0].evidence[0].url,'https://github.com/acme/repo/blob/deadbeef/src/a%20b.js#L12');
  assert.ok(r.assumptions.some(s=>s.includes('subset')));
  assert.doesNotMatch(Review.html(r,true),/javascript:/);
});

test('HTML escapes repository/report content, and the portable export preserves raw data safely', () => {
  const evil={target:{display:'<img src=x onerror=alert(1)>'},notes:['</script><script>alert(2)</script>'],agents:[{name:'<script>oops</script>',checks:[{id:'" onclick="alert(1)',name:'<svg onload=alert(1)>',status:'fail',severity:'high',remediation:'<script>bad()</script>'}]}]};
  const html=Review.standalone(evil,'body{color:black}');
  assert.doesNotMatch(html,/<img src=x|<svg onload|<script>alert|<script>bad/);
  assert.match(html,/&lt;img/);
  assert.equal((html.match(/<script/g)||[]).length,1);
  const embedded=html.match(/type="application\/json">([\s\S]*?)<\/script>/)[1];
  assert.deepEqual(JSON.parse(embedded),evil);
  assert.doesNotMatch(html,/data-review-check/);
});

test('both human-readable exports include all review sections and real check IDs', () => {
  const r=Review.build(sample),md=Review.markdown(r),html=Review.standalone(sample,fs.readFileSync(new URL('../assets/report-review.css',import.meta.url),'utf8'));
  for(const name of ['Findings & next steps','What we learned','Agent observations','Assumptions & open questions','Unevaluated checks']) assert.ok(md.includes(name),name);
  for(const f of r.failures) {assert.ok(md.includes(f.id));assert.ok(html.includes(f.id));}
  assert.ok(html.includes('viewport'));
  assert.ok(html.includes('@media print'));
  assert.doesNotMatch(md,/COMPLETED|zero-regression|complete tree coverage/i);
});
