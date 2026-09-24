# Security AI Agents — Competitor Landscape Report

Date: 2026-09-08
Goal: who's in the security AI-agent market, what they do, and whether Cerberus overlaps.
Cerberus refs: `murderszn/cerberus` + https://cerberus-github-auth.jjohnso75.workers.dev/agent

Cerberus baseline: 9-agent browser swarm; GitHub OAuth account sign-in + separate repo access + tab-only PAT; Pollinations multi-model (GPT/Claude/Gemini/Kimi/Qwen); outputs Security Scorecard + Suggested PR patch / draft-PR + Agent Engineering Plan + AI analyst report.

## 1. Established (platform incumbents)

- **Wiz Defend + Blue Agent (Google)** — cloud detection & response with AI auto-triage and verdict for cloud/AI workloads. No direct overlap: Cerberus is repo-centric AppSec, not cloud CDR.
- **CrowdStrike Charlotte AI** — endpoint-first AI triage, threat hunting, agentic SOAR inside Falcon + NG-SIEM. No direct overlap: endpoint/SOC vs. code review.
- **SentinelOne Purple AI** — generative-AI analyst over Singularity XDR/SIEM for natural-language hunt, triage, auto-remediation. No direct overlap.
- **Palo Alto Cortex XSIAM/XSOAR + Prisma AIRS** — platform SOC with AI triage, orchestration, AI-runtime protection. No direct overlap except pattern: triage → orchestration → remediation.
- **Darktrace Cyber AI Analyst / ActiveAI** — self-learning network AI that auto-investigates and triages every alert cross-domain. No overlap.
- **Microsoft Security Copilot** — copilot over Defender/Sentinel/Intune for guided triage, hunting, phishing response. No overlap: runtime SOC copilot vs. pre-merge review.
- **Google Gemini for SecOps** — AI investigation and CNAPP+XDR fusion with Mandiant intel after Wiz acquisition. No overlap.

Verdict on Established: you do NOT compete here. They define the crowded SOC-triage norm Cerberus avoids by staying in code/PR.

## 2. Startups / New entrants (agentic SOC — DIRECT overlap cluster)

Core overlap theme: autonomous Tier-1 triage/investigation/hunting. Triage is table stakes.

- **Dropzone AI | Agentic SOC: AI SOC Analyst (autonomous Tier-1 triage/investigation/evidence docs) + AI Threat Hunter (proactive hunt packs) | $37M Series B 2025, 100+ customers | DIRECT overlap on triage/investigation.**
- **Radiant Security | Agentic SOC copilot: deep triage on 100% of alerts, proposes tailored response | $15M | DIRECT overlap on full-coverage triage.**
- **Prophet Security | Agentic AI SOC platform: AI SOC Analyst (Tier1-3 triage/investigate/respond) + AI Threat Hunter + Detection Advisor, human-on-the-loop Guidance | $30M Series A, Amex/Citi Ventures | DIRECT overlap; differentiator is Guidance customization.**
- **Simbian | Autonomous SecOps multi-agent: SOC Agent + Pentest Agent + Threat Hunt Agent + GRC agents on Security Accelerator Platform, cross-agent coordination | DIRECT SOC overlap plus pentest/GRC adjacencies.**
- **7AI (Seven AI) | Agentic AI SOC: auto investigation across cloud/endpoint/identity/network, attack-path tracing, investigation packages; full-SOC-OS positioning | founded 2024 by Cybereason founders, $166M | DIRECT well-funded overlap.**
- **Torq Socrates | AI SOC + hyperautomation: virtual Tier-1 (triage/validate/enrich/investigate/escalate) + multi-agent framework + natural-language Agentic Builder | DIRECT overlap plus builder angle.**
- **BlinkOps | No-code security agent builder + AI SOC micro-agents across triage/investigate/respond/remediate | OVERLAP if your agent is a platform/builder.**
- **Tines** — orchestration-first AI workflow automation connecting SOC tools for triage/remediation. Adjacent: Cerberus has no workflow/orchestration layer.
- **Intezer / Exaforce** — autonomous triage and forensic investigation agents for SOC alert overload. No code overlap.
- **Aisera | Enterprise agentic-AI (ITSM/ITOps-adjacent, NOT pure SOC): AiseraGPT/AI Copilot/Unify, TRAPS governance, ITSM conversational AI leader | ADJACENT only; overlap only on ticket-resolution/copilot.**
- **New-entrant cluster 2025–2026 | Zero Cmd, Twine, Conifers, Legion, TENEX/AirMDR (AI MDR), Arctic Wolf Aurora Agentic SOC, Reliance RADAR (99.3% AI triage precision); Gartner tracks 'AI SOC Agents' since June 2025; CrowdStrike/Microsoft/Palo Alto/SentinelOne/Zscaler all ship agentic SOC | MARKET crowded: triage is table stakes; differentiation in autonomy graduation, rollback, verification, integrations, hunt/pentest/GRC.**

## 3. Open-source / frameworks (closest to Cerberus code-review loop)

- **OpenAI codex-security CLI (npm @openai/codex-security, Apache-2.0)** — LLM contextual vuln find/validate/fix on Codex agent; pattern-match + patch proposals. Direct agentic-remediation competitor to Suggested-PR loop.
- **Snyk agent-scan (github.com/snyk/agent-scan)** — scanner for AI agents/MCP servers/skills; E*/W* codes, risk scores; abuse-gated API. Agent-surface security niche Cerberus does not address.
- **elvezjp/security-ai-scanner** — agentic read-only (Read/Glob/Grep, no shell/write) repo explorer tracing source-to-sink; SARIF 2.1.0 to GitHub Code Scanning. Closest OSS analog to Cerberus read phase.
- **byteray-ai/xpsd** — reachability triage agent feeding scanner output to LLM with ast-grep tools; SARIF + markdown; low-cost/no-full-repo-in-context design. Triage layer Cerberus lacks.
- **panpiii/security-ai-agent + sergey-ko/ai-sec** — pip-audit/Bandit+LLM summarizer action and OWASP ASVS/MASVS/CIS Claude skill. Lightweight OSS review competitors.
- **secblok/belay (OSS, local-first)** — tool-call boundary guard for Claude Code/Codex/Cursor/MCP blocking dangerous cmds, secret leaks, prompt injection; OWASP ASI/LLM Top10/ATLAS + SARIF. Agent-guardrail flank Cerberus lacks.
- **verwen/argus (OSS black-box red-team)** — 160–500+ probes vs HTTP/gRPC/browser agents, LLM-judged SARIF/JUnit/HTML, CI gate. Agent-vs-agent testing entrant.
- **numasec / H-mmer/pentest-agents / kali-pentest + android-pentest-ai skills** — MCP-native pentest agents, 48-agent bounty framework, 199–200+ Kali CLI playbooks for Claude/Codex/Gemini/Cursor. Offensive-agent market Cerberus does not cover.
- **Semgrep OSS Engine + Pro + Assistant/Multimodal + Claude plugin + Replit Guardian integration** — 30+ langs, 600+ Pro rules, semgrep ci, AI triage/remediation. Deterministic-SAST+AI incumbent every entrant is judged against.
- **Commercial auto-remediation wave (Pixee, Mobb, Qwiet AI AutoFix, Seal, Aikido, Maze, Nullify, Corgea, Kodem, Backline, Depthfirst, Stingrai Snipe)** — PR-gating checks + AutoFix PRs + bulk fixes; Snipe adds DAST+white-box+PR-gate. Monetized version of Cerberus Suggested-PR loop.
- **Cloudflare Workers GitHub-auth/agent stack: cloudflare/workers-oauth-provider (OAuth 2.1 for Workers/MCP), openma-ai/open-managed-agents (Workers/Durable Objects + Hono API)** — infra pattern matching Cerberus GitHub-auth Workers architecture, not a product competitor.

## 4. Gap analysis for Cerberus

You overlap DIRECTLY with: Dropzone AI, Radiant, Prophet, Simbian, 7AI, Torq, BlinkOps (if builder) on language of triage/investigation — but NOT on domain (they do SOC alerts; you do repos/PRs). Your real domain competitors are codex-security, elvezjp scanner, xpsd, Semgrep+AI, and the AutoFix-PR wave.

Gaps / opportunities:
1. No reachability triage (xpsd model) — you risk flagging unreachable vulns; add scanner → LLM triage filter.
2. No SARIF / Code Scanning output (elvezjp, xpsd, belay do this) — limits CI gating vs Semgrep.
3. Suggested-PR loop is unmoated — Pixee/Mobb/Aikido/Snipe already monetize it with PR-gates, bulk-fix, rollback/verification; you need verification + autonomy graduation to differentiate.
4. No agent-surface coverage (Snyk agent-scan) and no guardrail/testing flank (belay, argus) — growing niche you ignore.
5. No pentest/GRC/hunt adjacencies (Simbian, pentest-agents) — keep scope tight or explicitly roadmap.
6. Crowded-SOC lesson applies to you: per 2025–2026 cluster + Gartner AI SOC Agents tracking, triage alone is table stakes — win on verification, rollback, integrations, and Engineering Plan depth.
