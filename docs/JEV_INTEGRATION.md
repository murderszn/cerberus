# Jev security review triage

This opt-in Python adapter fetches the default GitHub branch at an immutable
commit, then sends eligible source files to TypeSafe's Jev API. It does not run
repository code. Normal Cerberus scans do not invoke Jev.

## Run

Set `JEV_API_KEY` in your environment or `JEV_API_KEY` / `jev_api_key` in the
current directory's `.env` (do not commit it). Environment values take precedence;
the CLI reads literal values without executing shell expressions. Optionally set
`GITHUB_TOKEN` for private repositories or higher GitHub rate limits. Invoking
this command sends redacted source to TypeSafe and may incur API charges:

```sh
python -m servers.jev https://github.com/owner/repo \
  --criteria vulnerabilities "quality issues" maintainability > triage.json
```

Only send repositories you are authorized to share with TypeSafe. Filename
exclusions and redaction are best-effort, not a guarantee that source contains
no confidential information. Review the code and provider policies beforehand.

## Python integration

```python
import os
from servers.jev import integrate_jev_with_cerberus, integrate_with_cerberus

files = integrate_jev_with_cerberus(
    "https://github.com/owner/repo",
    {"api_key": os.environ["JEV_API_KEY"],
     "api_endpoint": "https://api.typesafe.ai/v1/systemone"},
    ["vulnerabilities", "quality issues", "maintainability"],
)
# Optionally attach to an existing Cerberus report for the SAME commit:
integrate_with_cerberus(files, report=cerberus_report)
```

The list contains paths, pinned commit URLs, status, priority, riskScore,
potentialRisks, and requiresReview. `riskScore` is 100 times the maximum concern
probability, **not a vulnerability severity or Cerberus security score**.
High priority starts at 0.7; medium at 0.4. All assessed files retain each
criterion's probability, even below those thresholds. Sort order is descending
riskScore with path as tie-breaker. Skipped files follow with `unassessed`
priority, null score, and an explicit reason; they are not declared safe.
Every result requires review. Jev does not produce finding descriptions or
line-level evidence here; native scanners and specialists must verify concerns.

`integrate_with_cerberus` attaches `cerberus.triage/1` under `report["triage"]`.
Cerberus's conversational scan digest includes this advisory queue. Native
scores, findings, SARIF, and policy gates are unchanged.

## Live browser visualization (local preview)

From the repository root, run `python3 -m servers.jev_live` alongside the static
preview at `http://127.0.0.1:8765/agent.html`. The bridge listens only on loopback
port 8766 and loads the Jev key from `.env`. It serves no files and accepts only
JSON POSTs from the exact localhost preview origins; keys are never returned to
the browser. Only one triage runs at a time.

Select **Jev · Live file intelligence** before starting a scan. Native checks run
first; Jev then uses the native report's exact commit. Real streamed events
update the candidate file map and high/medium/low review lanes. Select a tile
to inspect category probabilities; select it again to return to following the
latest file. Response timing includes the Jev HTTP round trip and any retries,
not just model inference. Total time also includes GitHub acquisition.

After completion, select **Open security report**. Advisory triage is included
in the report JSON. Cancellation stops the client stream; the server stops at
the next event write, although an in-flight API request may still complete and
be billed. Errors leave the native report available and never mark partial
triage as completed. Skipped files are explicitly unassessed.

The local agent screen also offers **Generate with Pollinations** after opening
the report. This sends a bounded summary of the native findings, exact commit,
and up to 20 assessed Jev file priorities to Pollinations through the same
loopback bridge. It runs only when selected; the API key remains server-side.
The synthesis is advisory and does not alter the native score. The bridge uses
the Cerberus saved credential or `POLLINATIONS_API_KEY`; a rejected credential
must be refreshed through the Cerberus CLI before generation can succeed.

The hosted page shows the option as unavailable. Cloudflare needs a separately
authenticated, quota-limited production bridge; the local key is not uploaded
or embedded into public assets.

## Contract and limits

The [documented API](https://docs.typesafe.ai/api) uses POST `/v1/systemone`,
bearer API-key authentication, `model`, `state`, and typed `questions`. Answers
are read from `answers`, not a presumed GitHub-analysis `data` endpoint. Each
file is sent as one state with independent Noul questions for the supplied
criteria. `api_secret` is accepted in the credentials dictionary but never
transmitted because the documented API does not use it. Custom endpoints are
rejected to prevent credential/source exfiltration.

- At most 100 eligible files, 64 KiB each, selected in path order; no truncation
  of individual files. File selection is bounded, not risk-ranked in advance.
- Source/config extensions are allowlisted. Binary files, symlinks, submodules,
  common generated/dependency folders and sensitive filenames are excluded.
- Root `.cerberusignore` supports case-sensitive path globs and directory
  prefixes; bare names match at any depth. Comments and blank lines are ignored
  (no gitignore negation).
- Truncated GitHub inventories fail explicitly. Private repositories require
  a GitHub token; credentials are never included in result objects.
- HTTPS endpoints are fixed; redirects are rejected; responses are bounded;
  requests time out after 30 seconds. Rate-limit/overload errors retry at most
  twice with exponential backoff. Other failures abort the run, with no
  misleading partial-success result. Retries can consume additional quota.
- Redaction may remove context and reduce model accuracy. File-local analysis
  does not see cross-file flows and cannot certify repository safety.

Tests (mocked GitHub and Jev; no credentials or network needed):

```sh
python -m unittest discover -s tests -p 'test_jev.py'
```
