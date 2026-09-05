# Security Policy

## Reporting a Vulnerability

Please report security issues privately rather than opening a public issue.

- Open a [private security advisory](https://github.com/murderszn/cerberus/security/advisories/new), or
- Email the maintainers with `SECURITY` in the subject line.

We aim to acknowledge reports within 2 business days and to ship a fix or a
mitigation plan within 30 days.

## Scope

Cerberus reads repository contents and evaluates them against a static native
check catalog. Native scanning and ALIGNMENT analysis execute no scanned code.
Optional feeder adapters execute explicitly allowlisted third-party scanner
binaries with argv-based subprocess calls, bounded output, and timeouts; they do
not execute commands discovered in repository content. Reports of particular interest:

- A crafted repository that causes the scanner to execute code, exfiltrate the
  user's GitHub token, or escape the browser sandbox.
- Cross-site scripting via finding snippets. Scanned source is attacker-authored
  by definition and is escaped before rendering — a bypass is a real finding.
- Token handling: the optional GitHub PAT is held in `sessionStorage` and sent
  only to `api.github.com`. Any path that leaks it elsewhere is a real finding.
- Feeder output that exposes a detected credential rather than a redacted value.
- Path traversal through an output path, unbounded scanner output, or a timeout
  bypass that can exhaust the host.
- ALIGNMENT content that Cerberus obeys as instructions instead of treating as
  untrusted evidence.

## Third-party scanners

Feeders are optional and are never downloaded automatically. Operators are
responsible for reviewing and pinning the exact Gitleaks, OSV-Scanner, Zizmor,
OpenSSF Scorecard, and actionlint binaries they install. These programs process
untrusted files and may access the network; isolate them, grant the minimum
permissions, verify upstream release provenance, and consult their own security
policies. Use `--native-only` for the smallest offline trust boundary.

Normalized reports omit secret values, but filenames, locations, dependency
names, and vulnerability descriptions can still be sensitive. Store JSON, HTML,
SARIF, and raw feeder artifacts with restricted access and an appropriate
retention period.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | yes       |
| < 2.0   | no        |
