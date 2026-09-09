# Gemini Enterprise 3P Connector Automation Tool

An enterprise-grade CLI tool for provisioning and configuring 3P data
connectors (Microsoft SharePoint Online Federated Search, OneDrive, Outlook,
Teams, Confluence, Jira) for **Gemini Enterprise (Discovery Engine)** on Google
Cloud.

---

## 1. Package Structure & Architecture

```
ge_connector_tool/
├── .github/
│   └── workflows/
│       └── test.yml                 # CI workflow (Terraform fmt, validate, test)
├── ge_connector_tool.py             # Main CLI Entry Point & Orchestrator
├── config_template.json             # Example configuration JSON
├── README.md                        # Package Documentation
├── core/
│   ├── logger.py                    # Redacting logger (scrubs secrets)
│   ├── rollback.py                  # Stack-based Rollback Manager
│   ├── preflight.py                 # Pre-flight Validation Engine
│   └── plugin_base.py               # Abstract Base Class for plugins
├── providers/
│   ├── entra_provider.py            # Microsoft Entra ID CLI / API provider
│   └── gcp_provider.py              # GCP Discovery Engine & Secret Manager
├── plugins/
│   └── sharepoint_federated.py      # SharePoint Federated Plugin
└── terraform/
    └── entra-connector/             # Terraform module for Entra People Data Connector
        ├── main.tf
        ├── variables.tf
        ├── providers.tf
        ├── data.tf
        ├── terraform.tfvars.example
        ├── scripts/
        │   └── update_sync_time.sh  # Post-provisioning sync time update
        └── tests/
            └── connector.tftest.hcl # Native Terraform unit tests
```

---

## 2. Prerequisites

Before running the tool, verify that the environment meets the following
requirements:

### A. Binaries & Environment
* Recommended: **Google Cloud Shell** (`shell.cloud.google.com`).
* Local Terminal Requirements:
  * **Python 3.8+**
  * **Google Cloud SDK (`gcloud`)**: Authenticated via `gcloud auth login`.
  * **Azure CLI (`az`)**: Authenticated via `az login`.

### B. Access & Permissions
* **Google Cloud Project**:
  * `roles/discoveryengine.admin` (Discovery Engine Admin)
  * `roles/secretmanager.admin` (Secret Manager Admin)
  * `roles/serviceusage.serviceUsageAdmin` (Service Usage Admin)
  * `roles/iam.workforcePoolAdmin` (Workforce Identity Pool Admin)
* **Microsoft Entra ID (Azure AD)**:
  * Minimum: `Cloud Application Administrator` (App & Secret creation).
  * Optional: `Global Administrator` (Enables automatic tenant-wide Admin
    Consent execution).

---

## 3. Quick Start & Execution Modes

### A. Interactive Mode (Default)
Launches a guided terminal wizard with sensible defaults:
```bash
python3 ge_connector_tool.py
```

### B. Dry-Run / Plan Mode
Simulates execution, validates permissions, and previews proposed API calls
without mutating any state:
```bash
python3 ge_connector_tool.py --dry-run
```

### C. Non-Interactive Config Mode
Executes automated setups via JSON configuration:
```bash
python3 ge_connector_tool.py --config config_template.json
```

---

## 4. Key Enterprise Capabilities

* **Zero-Trust Security**: Uses session-bound runtime tokens (`az login` +
  `gcloud auth`). No secrets or passwords are saved to disk. All log outputs
  automatically scrub sensitive OAuth tokens and secrets.
* **Entra Secret Expiration Sync**: Automatically checks Entra ID secret
  validity policies and sets matching expiration metadata & alert tags
  (`alert_before_days=30`) in GCP Secret Manager.
* **Conditional Admin Consent**: Automatically grants tenant-wide Admin Consent
  if run by a Global Admin. If run by a Cloud Application Admin, it gracefully
  generates direct Azure Portal links and manual instructions in the final
  report.
* **Stack-Based Automated Rollback**: Signal handlers (`SIGINT`, `SIGTERM`,
  unhandled exceptions) trap failures midway and execute LIFO cleanup of
  transient resources created during the session.
* **Extensible Connector Architecture**: Built on a `BaseConnectorPlugin`
  interface to easily add support for other 3P systems (OneDrive, Outlook,
  Teams, Confluence, Jira).

---

## 5. Terraform Infrastructure & CI

Terraform modules for infrastructure provisioning are located in the `terraform/` directory:

* **Entra Data Connector** (`terraform/entra-connector/`): Provisions the Google Discovery Engine Microsoft Entra ID (Azure AD) People Data Connector and configures periodic synchronization. See [terraform/entra-connector/README.md](terraform/entra-connector/README.md) for details.
* **Testing**: Plan-based unit tests use native `terraform test` with mock providers (`mock_provider "google"`), requiring no cloud credentials:
  ```bash
  cd terraform/entra-connector
  terraform init -backend=false
  terraform validate
  terraform test
  ```
* **CI/CD Workflow**: [`.github/workflows/test.yml`](.github/workflows/test.yml) runs on every push and pull request affecting Terraform files to ensure formatting (`terraform fmt`), syntax validity (`terraform validate`), and test assertions (`terraform test`) pass.

