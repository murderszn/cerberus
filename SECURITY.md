# Security Policy

## Reporting a Vulnerability

Please report security issues privately rather than opening a public issue.

- Open a [private security advisory](https://github.com/murderszn/cerberus/security/advisories/new), or
- Email the maintainers with `SECURITY` in the subject line.

We aim to acknowledge reports within 2 business days and to ship a fix or a
mitigation plan within 30 days.

## Scope

Cerberus reads public repository contents and evaluates them against a static
check catalog. It executes no scanned code. Reports of particular interest:

- A crafted repository that causes the scanner to execute code, exfiltrate the
  user's GitHub token, or escape the browser sandbox.
- Cross-site scripting via finding snippets. Scanned source is attacker-authored
  by definition and is escaped before rendering — a bypass is a real finding.
- Token handling: the optional GitHub PAT is held in `sessionStorage` and sent
  only to `api.github.com`. Any path that leaks it elsewhere is a real finding.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | yes       |
| < 2.0   | no        |
