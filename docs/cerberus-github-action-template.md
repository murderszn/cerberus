# Cerberus GitHub Actions template

This repository ships a reusable workflow template at:

```text
.github/workflow-templates/cerberus-security-review.yml
```

## Deploy to another repository

1. Copy the template into the target repository at `.github/workflows/cerberus.yml`.
2. Change the scanner checkout from `ref: main` to a reviewed Cerberus commit SHA.
3. Adjust `--fail-under 80` if the target repository uses a different gate.
4. Commit and push the workflow.
5. Review the GitHub Actions summary, uploaded JSON/HTML reports, and Code Security SARIF results.

The template scans pull requests, pushes to `main`, and manual dispatches. It checks out the application and the Cerberus scanner separately, excludes the scanner checkout from its own scan, emits JSON/HTML/SARIF reports, uploads artifacts, and fails when the scanner errors or scores below the threshold.

For a stable security supply chain, pin both action versions and the Cerberus checkout to reviewed commit SHAs before deploying broadly.
