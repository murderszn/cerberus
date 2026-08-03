# Treasury & Banking Setup Guide: Cerberus Labs Inc.

This document details the corporate banking setup, payment gateways, and cash flow policies for **Cerberus Labs Inc.**

---

## 1. Corporate Bank Account Setup
The Corporation will establish its primary business banking relationship with a tech-focused bank (e.g., Mercury or Brex) to manage cash flow and operational capital.
* **Requirements for Opening Account**:
  - Certificate of Incorporation (Delaware).
  - Filed Employer Identification Number (EIN) confirmation letter (IRS Form CP 575 or Form 147C).
  - Action of Sole Incorporator and Adopted Bylaws.
  - Government-issued IDs and addresses for all founders/signatories.
* **Authorized Signatories**:
  - Joshua Johnson (CEO / CFO): Full access, wire approval authority, debit card administration.
  - Caleb Johnson (COO): Read-only access for operational oversight.
  - Elijah Johnson (CTO): Read-only access.

---

## 2. Payment Gateway & Merchant Account
To automate transaction flows for our point-in-time audits and continuous subscriptions, we will integrate a card processor.
* **Provider**: Stripe.
* **Configuration Tiers**:
  - **Stripe Billing**: Automates the $39/mo and $149/mo Watchdog continuous monitoring subscriptions, handling card updates and subscription lifecycle.
  - **Stripe Checkout**: Handles immediate one-off payments for the $99 Pro Examination Scan.
* **Settlement**: Payments are settled to the primary corporate checking account on a rolling 2-day basis.

---

## 3. Cash Management & Expense Control Policies
* **Operational Expense Account**: A dedicated checking account used for monthly recurring software subscriptions, server costs, and small marketing expenses.
* **Reserve Account**: Cash reserves representing 3-6 months of operational runway will be placed in a yield-generating corporate savings account.
* **Spending Limits**:
  - Debit cards will be issued to founders with strict daily limits ($1,000 limit for COO and CTO).
  - Individual expenses exceeding $2,500 require approval from the CFO (Joshua Johnson).
  - Corporate wire transfers exceeding $5,000 require dual approval from the CEO and COO.
