# Privacy Policy: Cerberus Labs Inc.

*Last Updated: August 2, 2026*

At **Cerberus Labs Inc.** ("Cerberus", "we", "us", or "our"), we are committed to protecting the code, data, and configurations you submit to our security examination services. This Privacy Policy details how we handle, process, and protect your information when you use our website (cerberus.ai), local repositories, or cloud APIs.

---

## 1. Information We Collect
In order to perform security examinations and monitoring, we collect the following data categories:
* **User Information**: Name, email address, company name, and payment information (processed securely via Stripe).
* **Repository and URL Data**: Source code, directory configurations, container files, and host URLs submitted for scanning.
* **Telemetry and Audit Logs**: Metadata regarding scan times, found vulnerabilities, severity levels, and execution logs of our agent swarm.

---

## 2. Code Processing and Zero-Knowledge Runtimes
We enforce strict data isolation protocols to protect your IP:
* **Stateless Container Analysis**: When you submit a GitHub repository for review, the codebase is pulled into an isolated, stateless WebAssembly (WASM) container.
* **No Code Persistence**: Once the 151-point scan finishes and the report is generated, the code and container are permanently destroyed from our scanning nodes. We do not store or mirror your codebase.
* **No AI Training Use**: We explicitly do not use, sell, or leverage your source code, configuration files, or database schemas to train base AI models.

---

## 3. How We Use Your Information
We use the collected information to:
* Execute security examinations and calculate application security scores.
* Generate and deliver interactive vulnerability reports.
* Coordinate continuous monitoring scans (Watchdog subscription tier) triggered by your deployment pipelines.
* Settle payments and prevent fraudulent requests.

---

## 4. Data Sharing and Sub-processors
We do not sell your personal data or source code to third parties. We share information only with trusted service providers necessary to deliver our services (our sub-processors):
* **Payment Processing**: Stripe (secure tokenized card transactions).
* **Cloud Infrastructure**: AWS / Google Cloud (hosting isolated WASM runtimes).
* **Transactional Email**: Resend (delivering audit reports).

---

## 5. GDPR & CCPA Compliance Rights
Depending on your residency, you possess specific data protection rights under the General Data Protection Regulation (GDPR) and California Consumer Privacy Act (CCPA):
* **Right of Access**: You may request a copy of the personal data we store (e.g., account profile and scan history metadata).
* **Right of Deletion (Erasure)**: You can request that we permanently delete your account, personal data, and scan histories from our databases.
* **Right to Data Portability**: You may request an export of your account metadata in a structured, machine-readable format.

---

## 6. Contact Information
If you have questions regarding this Privacy Policy or wish to request data deletion, contact us at:  
**Cerberus Labs Inc.**  
Email: privacy@cerberuslabs.com  
Web: cerberuslabs.com/privacy  
