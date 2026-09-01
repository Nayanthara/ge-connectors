# Gemini Enterprise 3P Connector Automation Tool

An enterprise-grade CLI tool for provisioning and configuring 3P data
connectors (Microsoft SharePoint Online Federated Search, OneDrive, Outlook,
Teams, Confluence, Jira) for **Gemini Enterprise (Discovery Engine)** on Google
Cloud.

---

## 1. Package Structure & Architecture

```
ge_connector_tool/
├── ge_connector_tool.py             # Main CLI Entry Point & Orchestrator
├── config_template.json             # Example configuration JSON
├── README.md                        # Package Documentation
├── tarraform_templates/             # Reusable Terraform HCL Templates
│   └── sharepoint_federated/        # SharePoint Federated Search Templates
├── core/
│   ├── logger.py                    # Redacting logger (scrubs secrets)
│   ├── rollback.py                  # Stack-based Rollback Manager
│   ├── preflight.py                 # Pre-flight Validation Engine
│   └── plugin_base.py               # Abstract Base Class for plugins
├── providers/
│   ├── entra_provider.py            # Microsoft Entra ID CLI / API provider
│   └── gcp_provider.py              # GCP Discovery Engine & Secret Manager
└── plugins/
    └── sharepoint_federated.py      # SharePoint Federated Plugin
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
  * **Terraform CLI (`>= 1.5.0`)**: required when applying generated Terraform files.

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

### B. Terraform Generation Mode (`--terraform`)
Generates parameterized Terraform HCL files in `terraform_ouput/` instead of directly provisioning:
```bash
# Interactive with Terraform file generation
python3 ge_connector_tool.py --terraform

# Non-interactive config with Terraform file generation
python3 ge_connector_tool.py --terraform --config config_template.json
```

### C. Dry-Run / Plan Mode
Simulates execution, validates permissions, and previews proposed API calls
without mutating any state:
```bash
python3 ge_connector_tool.py --dry-run
```

### D. Non-Interactive Config Mode
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
