# Cerberus — NPM Readiness Review & Publication Checklist

## Executive Summary

Cerberus provides an official Node.js npm launcher package located under `npm/cerberus-agent`. This package allows users to run the Cerberus security scanner and agent CLI directly via `npx cerberus-agent` or `npx cerberus`, without manual Python environment management.

This document serves as the official review and step-by-step checklist for publishing and maintaining `cerberus-agent` on the [npm Registry](https://www.npmjs.com/).

---

## 1. Technical Audit Results

| Audit Category | Status | Details / Implementation Notes |
| :--- | :---: | :--- |
| **Package Manifest** | ✅ PASS | `package.json` specifies name (`cerberus-agent`), version (`1.0.0-beta.0`), description, keywords, license (`MIT`), homepage, repository, bugs, and engines (`node >= 18`). |
| **Binary Mapping** | ✅ PASS | `"bin"` maps both `"cerberus"` and `"cerberus-agent"` to `"bin/cerberus.js"`, supporting both `npx cerberus-agent` and global installations (`npm install -g cerberus-agent`). |
| **Launcher Script** | ✅ PASS | `bin/cerberus.js` contains `#!/usr/bin/env node`, detects `python3`/`python`, enforces Python 3.10+ requirement, installs `cerberus[agent]` from GitHub, and forwards CLI arguments. |
| **Bundle Scope & Size** | ✅ PASS | `"files": ["bin", "README.md"]` excludes raw repo artifacts. Packed size is ~1.4 kB total. |
| **Automated Testing & Packaging** | ✅ PASS | `npm test` runs syntax check (`node --check bin/cerberus.js`) and `npm run pack:check` executes `npm pack --dry-run`. |
| **CI Integration** | ✅ PASS | `.github/workflows/ci.yml` runs npm syntax check and packaging dry-run on every push and pull request. |

---

## 2. Step-by-Step NPM Publication Checklist

### Phase 1: Technical & Codebase Preparation
- [x] Create package directory under `npm/cerberus-agent/` with clean structure.
- [x] Configure `package.json` with correct metadata, MIT license, repository links, and Node engine requirements (`>=18`).
- [x] Map binary entry points for both `cerberus-agent` and `cerberus` in `package.json`.
- [x] Implement shebang (`#!/usr/bin/env node`) and executable launcher script `bin/cerberus.js`.
- [x] Add Python 3.10+ runtime detection and error messaging in launcher.
- [x] Verify package tarball contents with `npm pack --dry-run` to ensure no unnecessary files are published.
- [x] Add `npm test` and `npm run pack:check` package scripts.
- [x] Integrate npm launcher verification into GitHub Actions CI (`.github/workflows/ci.yml`).

### Phase 2: NPM Account & Scope Setup
- [ ] **Step 2.1: Register / Log In to NPM Account**
  - Ensure the publishing account exists on [npmjs.com](https://www.npmjs.com/).
  - Enable Two-Factor Authentication (2FA) on the npm account (required for publishing).
  - Run local login from terminal:
    ```bash
    npm login
    ```
- [ ] **Step 2.2: Verify Package Name Availability**
  - Check if `cerberus-agent` is available on the registry:
    ```bash
    npm view cerberus-agent
    ```
  - Note: If `cerberus-agent` is claimed by an unrelated party, consider publishing under a scope (e.g. `@cerberus/agent` or `@murderszn/cerberus-agent`).

### Phase 3: Initial Release & Registry Publication
- [ ] **Step 3.1: Navigate to Package Directory**
  ```bash
  cd npm/cerberus-agent
  ```
- [ ] **Step 3.2: Run Final Pre-publish Checks**
  ```bash
  npm test
  npm run pack:check
  ```
- [ ] **Step 3.3: Publish Beta Release to Registry**
  - Publish with public access and `beta` tag:
    ```bash
    npm publish --access public --tag beta
    ```
  - For GA release (`1.0.0`):
    ```bash
    npm publish --access public
    ```

### Phase 4: Post-Publication Verification
- [ ] **Step 4.1: Test `npx` Execution from Remote Registry**
  ```bash
  npx cerberus-agent --help
  ```
- [ ] **Step 4.2: Test Global Installation**
  ```bash
  npm install -g cerberus-agent
  cerberus --version
  ```
- [ ] **Step 4.3: Verify NPM Package Page**
  - Confirm README rendered correctly at `https://www.npmjs.com/package/cerberus-agent`.
  - Confirm links to GitHub repository and issue tracker work.

### Phase 5: Continuous Publishing & Release Automation (Optional)
- [ ] **Step 5.1: Create NPM Granular Access Token**
  - Generate an npm access token (Automation or Publish type) on [npmjs.com](https://www.npmjs.com/settings/tokens).
  - Add token to GitHub repository secrets as `NPM_TOKEN`.
- [ ] **Step 5.2: Configure Automated Publish Workflow**
  - Add GitHub Actions workflow `.github/workflows/publish-npm.yml` to trigger on release tag creation (e.g., `v*`).

---

## 3. Maintenance & Troubleshooting

- **Python Version Error**: If users get `cerberus-agent: Python 3.10+ is required`, guide them to install Python 3.10 or newer.
- **Permission Denied**: Ensure `bin/cerberus.js` has executable file permissions (`chmod +x bin/cerberus.js`) prior to `npm publish`.
- **Version Bumping**: Before publishing new versions, bump `"version"` in `npm/cerberus-agent/package.json` according to Semantic Versioning (`PATCH.MINOR.MAJOR` or `1.0.0-beta.X`).
