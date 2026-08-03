#!/usr/bin/env python3
"""Generate documentation/checks.html and docs/scanner-checks.md from checks.json.

checks.json is the single source of truth for the Cerberus check catalog (see
docs/IMPROVEMENTS.md §2.2/§6). This script is the *only* thing that should ever
write those two files — do not hand-edit either one, and do not regenerate
checks.html from the markdown spec (that was the old, backwards arrangement).

Usage:
    python3 scripts/generate-checks-docs.py

Idempotent: re-running produces byte-identical output for an unchanged
checks.json.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS_JSON = ROOT / "checks.json"
OUT_HTML = ROOT / "documentation" / "checks.html"
OUT_MD = ROOT / "docs" / "scanner-checks.md"

# Fixed display order for agent sections (does not need to match checks.json's
# internal ordering of the "agents" array). Falls back to json order for any
# agent not listed here.
AGENT_ORDER = [
    "sentinel", "gatekeeper", "vault", "conduit",
    "watchtower", "librarian", "shield", "auditor", "architect",
]

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def load_catalog():
    data = json.loads(CHECKS_JSON.read_text(encoding="utf-8"))
    agents_by_id = {a["id"]: a for a in data["agents"]}
    checks_by_agent = {a["id"]: [] for a in data["agents"]}
    for c in data["checks"]:
        checks_by_agent.setdefault(c["agent"], []).append(c)

    order = [a for a in AGENT_ORDER if a in agents_by_id]
    order += [a["id"] for a in data["agents"] if a["id"] not in order]

    return data, agents_by_id, checks_by_agent, order


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

HEADER_SVG = (
    '<svg width="0" height="0" style="position:absolute">'
    '<symbol id="i-cerb" viewBox="0 0 24 24">'
    '<path d="M5 9.5 3.2 5l4.7 2.1L12 4l4.1 3.1L20.8 5 19 9.5c.7 1.2 1 2.6 1 4 0 3.7-3.6 6.5-8 6.5s-8-2.8-8-6.5c0-1.4.3-2.8 1-4Z" '
    'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>'
    '<path d="M8 11.5h.01M12 10h.01M16 11.5h.01M10 15.5c1.2.8 2.8.8 4 0" fill="none" '
    'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></symbol>'
    '<symbol id="i-search" viewBox="0 0 24 24"><circle cx="10.8" cy="10.8" r="6.3" fill="none" '
    'stroke="currentColor" stroke-width="1.8"/><path d="m16 16 5 5" fill="none" stroke="currentColor" '
    'stroke-width="1.8"/></symbol></svg>'
)


def page_header(active="checks", agent_order=None):
    def link(href, label, id_):
        cls = "sidebar-link active" if id_ == active else "sidebar-link"
        return f'<a class="{cls}" href="{href}">{label}</a>'

    agent_links = "\n    ".join(
        f'<a class="sidebar-link" href="#{aid}">{aid.upper()}</a>' for aid in (agent_order or [])
    )

    return f'''<header class="docs-header">
  <nav class="left">
    <a class="brand-mini" href="../cerberus.html">
      <span class="brand-mark"><svg><use href="#i-cerb"/></svg></span>
      <span>CERBERUS DOCS</span>
    </a>
    <a class="nav-link" href="../cerberus.html">Platform</a>
    <a class="nav-link" href="agents.html">Agents</a>
    <a class="nav-link" href="checks.html">Checks</a>
  </nav>
  <nav class="right">
    <form class="search-form" onsubmit="return false">
      <svg class="search-icon"><use href="#i-search"/></svg>
      <input class="search-input" placeholder="Search docs…" aria-label="Search docs">
    </form>
    <a class="nav-link" href="../cerberus-report.html" target="_blank">Sample Report</a>
    <button class="menu-toggle" aria-label="Open menu">☰</button>
  </nav>
</header>

<div class="docs-shell">
  <aside class="docs-sidebar">
    <div class="sidebar-title">Get Started</div>
    {link("index.html", "Overview", "index")}
    {link("quickstart.html", "Quickstart", "quickstart")}
    {link("scanner.html", "CLI Scanner", "scanner")}
    {link("reports.html", "Reading Reports", "reports")}

    <div class="sidebar-title">Architecture</div>
    {link("agents.html", "Agent Swarm", "agents")}
    {link("checks.html", "Check Catalog", "checks")}
    {link("scoring.html", "Severity & Scoring", "scoring")}

    <div class="sidebar-title">Check Categories</div>
    {agent_links}

    <div class="sidebar-title">Support</div>
    {link("faq.html", "FAQ", "faq")}
    {link("security.html", "Security & Privacy", "security")}
  </aside>

  <main class="docs-content">'''


PAGE_FOOTER = '''</main>
</div>

<footer class="docs-footer">
  <div class="inner">
    <span>© 2026 Cerberus Intelligence. All rights reserved.</span>
    <span><a href="index.html">Docs home</a> · <a href="agents.html">Agents</a> · <a href="scoring.html">Scoring</a></span>
  </div>
</footer>

<script src="assets/docs.js"></script>
</body>
</html>
'''


def build_check_card(c: dict) -> str:
    sev = c["severity"]
    parts = [f'<div class="check-card" id="{esc(c["id"])}">']
    parts.append('<div class="check-card-head">')
    parts.append(f'<span class="check-id">{esc(c["id"])}</span>')
    parts.append(f'<h4>{esc(c["name"])}</h4>')
    parts.append(f'<span class="sev {esc(sev)}">{esc(sev)}</span>')
    if c.get("cwe") and c["cwe"] != "N/A":
        parts.append(f'<span class="cwe-tag">{esc(c["cwe"])}</span>')
    parts.append('</div>')
    parts.append(f'<p>{esc(c["summary"])}</p>')
    parts.append('<div class="field-label">Risk</div>')
    parts.append(f'<p>{esc(c["risk"])}</p>')
    parts.append('<div class="field-label">Remediation</div>')
    parts.append(f'<p>{esc(c["remediation"])}</p>')
    fix = c.get("fix")
    if fix:
        parts.append('<div class="field-label">Suggested fix</div>')
        parts.append(f'<pre><code class="lang-{esc(fix.get("lang", "text"))}">{esc(fix["body"])}</code></pre>')
    parts.append('</div>')
    return "\n".join(parts)


def build_checks_html():
    data, agents_by_id, checks_by_agent, order = load_catalog()
    total = len(data["checks"])
    weight_sum = sum(a["weight"] for a in data["agents"])

    agent_index_rows = []
    sections = []
    for aid in order:
        agent = agents_by_id[aid]
        checks = checks_by_agent.get(aid, [])
        agent_index_rows.append(
            f'<tr><td><a href="#{aid}">{esc(agent["name"])}</a></td>'
            f'<td>{esc(agent["domain"])}</td><td>{agent["weight"]}</td><td>{len(checks)}</td></tr>'
        )
        cards = "\n".join(build_check_card(c) for c in checks)
        sections.append(
            f'<section class="checklist-section" id="{aid}">'
            f'<h3><span>{esc(agent["name"])}</span><span class="count">{len(checks)} checks</span></h3>'
            f'{cards}'
            f'</section>'
        )

    html_out = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Check Catalog — Cerberus Documentation</title>
<meta name="description" content="The complete Cerberus check catalog: {total} checks across nine agent domains, generated directly from checks.json.">
<link rel="stylesheet" href="assets/docs.css">
</head>
<body>
{HEADER_SVG}

{page_header("checks", order)}
    <h1>Check Catalog</h1>
    <p class="lead">The complete set of checks Cerberus agents evaluate during every examination, generated directly from <code>checks.json</code> — the single source of truth shared by the web app, the CLI (<code>examine.py</code>), and this page. The catalog currently holds <strong>{total} checks</strong> across nine agent domains, weighted to {weight_sum} points.</p>

    <div class="callout info">
      <div class="callout-title">How this catalog is built</div>
      <p>Every check below is read straight from <code>checks.json</code> by <code>scripts/generate-checks-docs.py</code>. Nothing here is hand-written or aspirational — if a check is not in <code>checks.json</code>, it does not run, and it is not listed here. For planned checks that are not yet implemented, see the roadmap section of <a href="../docs/examination-spec.md">the examination spec</a>.</p>
    </div>

    <h2>Check states</h2>
    <p>Every check resolves to exactly one of four states when a scan runs:</p>
    <div class="check-states">
      <div class="check-state"><strong>pass</strong>Applicable, evaluated, clean.</div>
      <div class="check-state"><strong>fail</strong>Applicable, evaluated, one or more findings.</div>
      <div class="check-state"><strong>not_applicable</strong>Precondition unmet (e.g. no Dockerfile), with the reason stated.</div>
      <div class="check-state"><strong>skipped</strong>Could not be evaluated (file budget exhausted, fetch error), with the reason stated.</div>
    </div>

    <h2>Agent index</h2>
    <table class="agent-index">
      <thead><tr><th>Agent</th><th>Domain</th><th>Weight</th><th>Checks</th></tr></thead>
      <tbody>
      {chr(10).join(agent_index_rows)}
      <tr><td colspan="2"><strong>Total</strong></td><td><strong>{weight_sum}</strong></td><td><strong>{total}</strong></td></tr>
      </tbody>
    </table>

{chr(10).join(sections)}

    <div class="callout tip">
      <div class="callout-title">Want the scoring math?</div>
      <p>See <a href="scoring.html">Severity & Scoring</a> for how per-check deductions, hit caps, and agent weights combine into the final 0–100 score.</p>
    </div>
{PAGE_FOOTER}'''
    OUT_HTML.write_text(html_out, encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({total} checks)")


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def build_scanner_checks_md():
    data, agents_by_id, checks_by_agent, order = load_catalog()
    total = len(data["checks"])
    weight_sum = sum(a["weight"] for a in data["agents"])

    lines = []
    lines.append("# Cerberus Check Catalog")
    lines.append("")
    lines.append(
        "This document is generated directly from `checks.json` by "
        "`scripts/generate-checks-docs.py` — do not hand-edit it. `checks.json` is the "
        "single source of truth consumed by the web app, `examine.py`, and this page "
        "(see `docs/IMPROVEMENTS.md` §2.2/§6)."
    )
    lines.append("")
    lines.append(f"**Total: {total} checks across 9 agents, weighted to {weight_sum} points.**")
    lines.append("")
    lines.append(
        "Every check resolves to one of four states at scan time: `pass`, `fail`, "
        "`not_applicable` (precondition unmet, reason stated), or `skipped` (could not "
        "be evaluated, reason stated)."
    )
    lines.append("")
    lines.append("## Agent index")
    lines.append("")
    lines.append("| Agent | Domain | Weight | Checks |")
    lines.append("|---|---|---|---|")
    for aid in order:
        agent = agents_by_id[aid]
        checks = checks_by_agent.get(aid, [])
        lines.append(f"| {agent['name']} | {agent['domain']} | {agent['weight']} | {len(checks)} |")
    lines.append(f"| **Total** |  | **{weight_sum}** | **{total}** |")
    lines.append("")
    lines.append("## Summary table")
    lines.append("")
    lines.append("| Agent | ID | Check | Severity | CWE |")
    lines.append("|---|---|---|---|---|")
    for aid in order:
        agent = agents_by_id[aid]
        for c in checks_by_agent.get(aid, []):
            lines.append(f"| {agent['name']} | {c['id']} | {c['name']} | {c['severity'].upper()} | {c.get('cwe', 'N/A')} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detailed checks")
    lines.append("")

    for aid in order:
        agent = agents_by_id[aid]
        checks = checks_by_agent.get(aid, [])
        lines.append(f"### {agent['name']} — {agent['domain']} ({len(checks)} checks, weight {agent['weight']})")
        lines.append("")
        for c in checks:
            lines.append(f"#### {c['id']}: {c['name']}")
            lines.append(f"* **Severity**: `{c['severity'].upper()}`")
            if c.get("cwe") and c["cwe"] != "N/A":
                lines.append(f"* **CWE**: {c['cwe']}")
            lines.append(f"* **Summary**: {c['summary']}")
            lines.append(f"* **Risk**: {c['risk']}")
            lines.append(f"* **Remediation**: {c['remediation']}")
            fix = c.get("fix")
            if fix:
                lines.append(f"* **Suggested fix**:")
                lines.append(f"  ```{fix.get('lang', 'text')}")
                for fl in fix["body"].split("\n"):
                    lines.append(f"  {fl}")
                lines.append("  ```")
            lines.append("")
        lines.append("---")
        lines.append("")

    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD} ({total} checks)")


def main():
    build_checks_html()
    build_scanner_checks_md()


if __name__ == "__main__":
    main()
