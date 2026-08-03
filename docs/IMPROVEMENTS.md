# Cerberus — Master Improvement Prompt

Everything that has to change to turn this from a demo into a deployable product.
This document is the shared contract for the build swarm. **Do not deviate from the
interfaces in §3 — other agents are building against them in parallel.**

---

## 1. The core defect

`index.html` contains `mockFindingsDB`, a hardcoded object of 27 invented findings.
`generateReportData()` sums their severities to a constant 56-point penalty, so **every
target scores exactly 44/100 (F)** regardless of what was typed into the box. The
`/scan` fetch path only fires on `localhost`, and silently falls back to the same mock
on any error. Nothing about the output is derived from the target.

**Required outcome:** two different repositories must produce two different scores,
different findings, and different file citations — because the files were actually read.

---

## 2. What "working" means

### 2.1 Real acquisition
- Parse a GitHub URL (`https://github.com/{owner}/{repo}`, with or without
  `.git`, `/tree/{ref}`, trailing slash) into `{owner, repo, ref}`.
- `GET https://api.github.com/repos/{owner}/{repo}` → default branch, license,
  description, stars, archived, pushed_at, size.
- `GET .../git/trees/{sha}?recursive=1` → the complete file list.
- Fetch file contents from `https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{path}`.
  raw.githubusercontent is a CDN and is not subject to the 60/hr API rate limit, so
  content fetching must go through it — **never** through the contents API.
- Optional PAT field: if the user supplies a token, send it as
  `Authorization: Bearer <tok>` on api.github.com calls only (never to raw), and
  surface the resulting rate-limit headroom.
- Budget: ≤ 400 files fetched, ≤ 512 KB per file, 8-way concurrency, hard 90 s wall clock.
  Prioritise: manifests and config > top-level source > `src/`, `app/`, `lib/`, `api/`
  > everything else. Report what was skipped and why — never silently truncate.

### 2.2 Real evaluation
- The check catalog lives in **`/checks.json`** and nowhere else. 51 checks across
  9 agents. Web, CLI, and docs all consume that one file.
- Every check resolves to exactly one of four states:
  - `pass` — applicable, evaluated, clean
  - `fail` — applicable, evaluated, one or more findings
  - `not_applicable` — precondition unmet (no Dockerfile → skip Docker checks),
    with the reason stated
  - `skipped` — could not evaluate (file budget exhausted, fetch error), with the reason
- Findings carry: file path, line number, the matched line as a snippet,
  and a permalink `https://github.com/{o}/{r}/blob/{sha}/{path}#L{n}` — pinned to the
  scanned SHA so the link never rots.

### 2.3 Real scoring
- Start from each agent's `weight` in `checks.json` (sums to 100).
- Deduct `per_hit[severity] × min(hits, hit_cap)` per failed check; floor each agent at 0.
- Total = sum of agent scores. Grade A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, else F.
- A clean, well-run repository must be able to score in the 90s. If a healthy
  reference repo (see §5) cannot break 80, the checks are too noisy — fix the checks.

### 2.4 False positives are the product risk
- Honour `exclude_tests`, `not_match`, `skip_if_placeholder`, and `global_exclude`.
- Never scan minified bundles, lockfiles, vendored code, or `node_modules`.
- Placeholder filter must eat `your_api_key_here`, `<TOKEN>`, `${VAR}`, `process.env.X`,
  `example`, `changeme`, `xxxx`.
- When confidence is inherently low (R-01 hardcoded IP, C-04 cleartext HTTP), cap hits
  and keep the severity low. A finding a user dismisses twice costs more trust than
  a finding you never made.

---

## 3. Interface contract — DO NOT CHANGE

### 3.1 `assets/checks.js`
Generated from `checks.json` by `scripts/build-checks.py`. Assigns a single global:
```js
window.CERBERUS_CHECKS = { /* verbatim contents of checks.json */ };
```
It is a build artifact. Never hand-edit it; edit `checks.json` and rebuild.

### 3.2 `assets/scanner.js`
```js
window.CerberusScanner = {
  parseTarget(input) -> { kind: 'github'|'website'|'package'|'unknown', owner?, repo?, ref?, url? },
  scan(target, opts) -> Promise<Report>,   // opts: { token, onProgress, signal }
};
```
`onProgress(evt)` is called with:
```js
{ phase: 'resolving'|'tree'|'fetching'|'evaluating'|'scoring'|'done',
  agentId?: string, pct: 0..100, message: string,
  filesFetched?: number, filesTotal?: number }
```

### 3.3 The `Report` object — every consumer depends on this shape
```jsonc
{
  "schema": "cerberus.report/2",
  "target":  { "kind":"github", "display":"owner/repo", "url":"https://github.com/o/r",
               "owner":"o", "repo":"r", "ref":"main", "sha":"abc123…" },
  "scannedAt": "2026-08-02T18:40:00Z",
  "engine":  { "version":"2.0.0", "checksVersion":"2.0.0", "source":"web"|"cli" },
  "score": 87.5,
  "grade": "B",
  "counts": { "critical":0, "high":2, "medium":5, "low":3,
              "pass":38, "fail":9, "not_applicable":3, "skipped":1, "total":51 },
  "repo":  { "description":"…", "stars":1234, "license":"MIT", "archived":false,
             "pushedAt":"2026-07-30T…", "primaryLanguage":"TypeScript" },
  "coverage": { "filesInTree":842, "filesEligible":310, "filesScanned":310,
                "filesSkipped":0, "bytesScanned":4210233, "truncated":false,
                "skipReasons":{} },
  "agents": [
    { "id":"sentinel", "name":"SENTINEL", "domain":"Code Analysis",
      "weight":14, "score":12.0,
      "checks": [
        { "id":"S-01", "name":"Hardcoded credential assignment", "severity":"critical",
          "status":"pass"|"fail"|"not_applicable"|"skipped",
          "reason":"No Dockerfile in repository",        // present unless status==fail
          "cwe":"CWE-798", "summary":"…", "risk":"…", "remediation":"…",
          "fix": { "lang":"diff", "body":"…" },
          "deduction": 4.0,
          "findings": [
            { "path":"src/config/db.py", "line":42, "column":8,
              "snippet":"DB_PASSWORD = \"hunter2hunter2hunter2\"",
              "match":"DB_PASSWORD = \"hunter2…\"",
              "url":"https://github.com/o/r/blob/abc123/src/config/db.py#L42" }
          ],
          "findingsTruncated": false, "totalFindings": 1 }
      ] }
  ],
  "notes": [ "3 files exceeded the 512 KB limit and were not scanned." ]
}
```
Rules: `agents[]` always contains all 9. `checks[]` always contains every check for
that agent, including passes. A `fail` always has ≥1 finding **or** a `reason`
explaining a repository-level failure (e.g. "No SECURITY.md found").

### 3.4 `examine.py`
Must emit byte-identical schema. `python3 examine.py <path-or-github-url> --json out.json`.
`--fail-under 80` exits non-zero for CI use. `--sarif out.sarif` for code scanning upload.

---

## 4. The site is a product, not a slideshow

Current app is three `display:none` divs and a `resetApp()` that wipes state. Required:

1. **Hash routing, no state loss.** `#/` splash · `#/scan/{owner}/{repo}` running ·
   `#/report/{owner}/{repo}` results · `#/report/{o}/{r}/{checkId}` deep-links one check.
   Browser back/forward work. Refreshing a report URL re-renders from cache, or
   re-scans if the cache is cold. A report URL is shareable.
2. **Persistence.** Cache reports in `localStorage` keyed by `owner/repo@sha`, 24 h TTL.
   A "Recent scans" list on the splash with score, grade, and timestamp.
3. **Full check visibility.** Default view shows all 51 checks grouped by agent, with
   filter chips: All · Failed · Passed · N/A, plus severity filters and a text search.
   Passed checks are collapsed but present — the score is not credible without them.
4. **Findings UI.** Each finding shows the snippet with its line number, a
   "View on GitHub" permalink, the CWE, and the suggested fix as a copyable block.
5. **Honest failure.** Rate limited → say so, show the reset time, offer the PAT field.
   Private/404 → say so. Non-GitHub URL → explain that browsers cannot fetch arbitrary
   origins (CORS) and hand over the exact CLI command. **Never fall back to fake data.**
6. **Export.** Download JSON, download the standalone HTML report, copy Markdown summary.
7. **Real progress.** The agent grid reflects actual evaluation, not a `setTimeout`
   parade. Never show a completed agent before its checks have run.
8. **Accessible + responsive.** Keyboard reachable, `aria-live` on progress, works at
   375 px, respects `prefers-reduced-motion`, no horizontal body scroll.

---

## 5. Acceptance test — this is the pass/fail gate

Scan both:
- **Target under test:** `https://github.com/oso95/scroll-world`
- **Healthy reference:** a mature OSS repo (e.g. `sst/opencode`, `pallets/flask`)

Assert:
1. The two scores differ by a meaningful margin, and neither is 44.
2. Every finding's `path` exists in that repo's tree, and its `line` contains the
   snippet claimed. Spot-check five permalinks by opening them.
3. The healthy reference scores ≥ 80. If not, the catalog is too noisy.
4. Check states sum: `pass + fail + not_applicable + skipped == 51` for both.
5. `examine.py` on a local clone produces the same findings as the web scan of the
   same SHA (allow differences only where the web file budget truncated).
6. Manually review 10 findings across both reports and record the false-positive rate.
   **Ship gate: ≤ 10%.** Anything above that, tighten the offending pattern.

---

## 6. Deploy readiness

- Static hosting only — no build step required to serve, works on GitHub Pages.
- Zero external runtime dependencies. No CDN scripts, no analytics, no trackers.
- `checks.json` fetched relative, with `assets/checks.js` as the `file://` fallback.
- CSP meta tag; no inline event handlers (`onclick=` in markup must go).
- All user-controlled strings HTML-escaped at render. Findings contain attacker-authored
  source code — treat every snippet as hostile input.
- `documentation/` reflects the real implemented checks and the real count. If the
  catalog holds 51 checks, the site does not claim 151.
