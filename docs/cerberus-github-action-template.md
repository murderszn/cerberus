# Cerberus GitHub Actions template

This repository ships a reusable workflow template at:

```text
.github/workflow-templates/cerberus-security-review.yml
```

## Deploy to another repository

1. Copy the template into the target repository at `.github/workflows/cerberus.yml`.
2. Change the scanner checkout from the documented example SHA to the reviewed Cerberus commit you approved. Use `ref: main` only for short-lived experimentation.
3. Adjust `--fail-under 80` if the target repository uses a different gate.
4. Commit and push the workflow.
5. Review the GitHub Actions summary, uploaded JSON/HTML reports, and Code Security SARIF results.

The template scans pull requests, pushes to `main`, and manual dispatches. It checks out the application and the Cerberus scanner separately, excludes the scanner checkout from its own scan, emits JSON/HTML/SARIF reports, uploads artifacts, and fails when the scanner errors or its **native** score is below the threshold.

For a stable security supply chain, pin both action versions and the Cerberus checkout to reviewed commit SHAs before deploying broadly.

## Native and feeder modes

The production template defaults to `native-only`, so it has no dependency on third-party scanner installation and retains the historical `--fail-under` behavior. A manual run can select `auto`; Cerberus then runs installed and applicable feeders and records unavailable tools as warnings. The template does not download executables.

For a feeder-enabled CI deployment, build or select a reviewed runner image containing exact tool versions, verify checksums/signatures where the upstream provides them, and record the pins in the workflow. Avoid floating package-manager installs such as `latest`. Suggested inventory fields are executable, exact version, source URL, checksum, upstream license, and review date. The current adapters are:

| Executable | Purpose | License |
|---|---|---|
| `gitleaks` | Secret discovery | MIT |
| `osv-scanner` | Dependency vulnerability discovery | Apache-2.0 |
| `zizmor` | GitHub Actions security analysis | MIT |
| `scorecard` | OpenSSF repository posture | Apache-2.0 |
| `actionlint` | Workflow syntax and semantic validation | MIT |

Applicability is determined before executable availability. Gitleaks scans
working-tree files only in Phase 1; OSV-Scanner requires a supported manifest,
lockfile, or SBOM; Zizmor and actionlint require GitHub Actions workflows; and
Scorecard requires Git metadata or GitHub repository context. Zizmor is invoked
offline. Cerberus applies `.cerberusignore` and excludes the nested `.cerberus/`
scanner checkout from feeder input as well as native checks.

When a specifically selected feeder is mandatory, pass both `--feeders <list>` and `--strict-feeders`. Strict mode makes unavailable, timed-out, malformed, and failed requested executions policy blockers. Without strict mode those conditions remain visible warnings. Policy status is included in reports but does not introduce a new implicit process failure; `--fail-under` remains the native-score gate.

The artifact upload includes the normalized main report, standalone HTML, SARIF,
and the feeder report when created. SARIF keeps native Cerberus results first and
adds runs per producer. Raw output is bounded and retained only when practical;
secret-bearing Gitleaks fields and source snippets that may contain credentials
are omitted. Treat all scanner output as sensitive security data and set artifact
retention and access accordingly.

## Security notes

External scanners process attacker-controlled repository content and expand the CI trust boundary. Use only reviewed binaries, run with least privilege and a timeout, avoid credentials unnecessary for the scan, and do not grant outbound network access unless the selected tool requires it and the risk is accepted. Cerberus uses argv-based execution and never evaluates repository-provided commands, but an external scanner may have its own parser vulnerabilities or telemetry behavior. Native-only mode is the offline fallback.
