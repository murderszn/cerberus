#!/usr/bin/env node
// Smoke test: loads assets/checks.js + assets/scanner.js into a minimal global
// context (no bundler) and runs the real engine against two live GitHub repos.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

globalThis.window = globalThis;

const checksSrc = fs.readFileSync(path.join(ROOT, 'assets', 'checks.js'), 'utf8');
const scannerSrc = fs.readFileSync(path.join(ROOT, 'assets', 'scanner.js'), 'utf8');

(0, eval)(checksSrc);
(0, eval)(scannerSrc);

const Scanner = globalThis.CerberusScanner;
if (!Scanner) {
  console.error('FAIL: window.CerberusScanner was not defined after loading scanner.js');
  process.exit(1);
}

const TARGETS = ['oso95/scroll-world', 'sst/opencode'];
const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN || null;

async function scanOne(input) {
  const target = Scanner.parseTarget(input);
  console.log(`\n=== ${input} -> parsed as`, target, '===');
  const report = await Scanner.scan(target, {
    token,
    onProgress: (evt) => {
      if (evt.phase === 'fetching' && evt.filesFetched != null) {
        process.stdout.write(`\r  fetching: ${evt.filesFetched}/${evt.filesTotal}   `);
      } else if (evt.phase !== 'fetching') {
        process.stdout.write(`\r  [${evt.phase}] ${evt.message}                    \n`);
      }
    }
  });
  return report;
}

function topFindings(report, n) {
  const all = [];
  for (const agent of report.agents) {
    for (const check of agent.checks) {
      for (const f of check.findings) {
        all.push({ severity: check.severity, checkId: check.id, name: check.name, ...f });
      }
    }
  }
  const order = { critical: 0, high: 1, medium: 2, low: 3 };
  all.sort((a, b) => order[a.severity] - order[b.severity]);
  return all.slice(0, n);
}

async function main() {
  const reports = {};
  for (const t of TARGETS) {
    const report = await scanOne(t);
    reports[t] = report;

    console.log(`\n--- ${t} ---`);
    console.log(`score: ${report.score}  grade: ${report.grade}`);
    console.log('counts:', report.counts);
    console.log('coverage:', report.coverage);
    console.log('top 10 findings:');
    for (const f of topFindings(report, 10)) {
      console.log(`  [${f.severity}] ${f.checkId} ${f.name} — ${f.path}:${f.line}`);
    }
  }

  // ------------------------------------------------------------------
  // Assertions
  // ------------------------------------------------------------------
  let failures = 0;
  function assertTrue(cond, msg) {
    if (cond) {
      console.log(`PASS: ${msg}`);
    } else {
      console.log(`FAIL: ${msg}`);
      failures++;
    }
  }

  const r1 = reports[TARGETS[0]];
  const r2 = reports[TARGETS[1]];

  assertTrue(r1.score !== r2.score, `scores differ (${r1.score} vs ${r2.score})`);
  assertTrue(r1.score !== 44 && r2.score !== 44, `neither score is 44 (${r1.score}, ${r2.score})`);

  for (const [name, report] of Object.entries(reports)) {
    const c = report.counts;
    const sum = c.pass + c.fail + c.not_applicable + c.skipped;
    assertTrue(sum === c.total, `${name}: pass+fail+not_applicable+skipped (${sum}) == total (${c.total})`);
  }

  let findingIssues = 0;
  for (const [name, report] of Object.entries(reports)) {
    for (const agent of report.agents) {
      for (const check of agent.checks) {
        for (const f of check.findings) {
          if (!f.path || typeof f.path !== 'string' || f.path.length === 0) findingIssues++;
          if (!(f.line >= 1)) findingIssues++;
          if (!f.url || f.url.indexOf(report.target.sha) === -1) findingIssues++;
        }
      }
    }
  }
  assertTrue(findingIssues === 0, `every finding has non-empty path, line >= 1, permalink containing scanned SHA (${findingIssues} issues)`);

  console.log(failures === 0 ? '\nALL ASSERTIONS PASSED' : `\n${failures} ASSERTION(S) FAILED`);
  process.exit(failures === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error('FATAL:', err);
  process.exit(1);
});
