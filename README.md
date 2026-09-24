# Gemini Enterprise 3P Connector Automation Tool

An enterprise-grade automation framework and CLI orchestrator for provisioning, configuring, and managing third-party data connectors (**Microsoft SharePoint Online**, **OneDrive**, **Outlook**, **Teams**, and **Custom MCP**) for **Gemini Enterprise (Discovery Engine)** on Google Cloud.

The tool provides an interactive terminal wizard, non-interactive JSON configuration, non-mutating `--dry-run` simulation, production-ready **Terraform IaC generation**, stack-based LIFO automated rollback, and GCP Secret Manager vaulting with CMEK encryption and expiration syncing.

---

## Table of Contents
1. [Architecture & Package Structure](#1-architecture--package-structure)
2. [Supported Connectors & Architectural Modes](#2-supported-connectors--architectural-modes)
3. [User Guide: Step-by-Step Provisioning & Workflows](#3-user-guide-step-by-step-provisioning--workflows)
   - [Workflow A: Interactive Terminal Wizard (Quickstart)](#workflow-a-interactive-terminal-wizard-quickstart)
   - [Workflow B: Scripted / Non-Interactive Automation](#workflow-b-scripted--non-interactive-automation)
   - [Workflow C: Dry-Run / Change Plan Simulation](#workflow-c-dry-run--change-plan-simulation)
   - [Workflow D: Terraform Infrastructure as Code (IaC) Export](#workflow-d-terraform-infrastructure-as-code-iac-export)
   - [Post-Setup: Admin Consent & Gemini Enterprise Authorization](#post-setup-admin-consent--gemini-enterprise-authorization)
4. [CLI Command-Line Flag Reference](#4-cli-command-line-flag-reference)
5. [Configuration File Specification (`config_template.json`)](#5-configuration-file-specification-config_templatejson)
6. [Enterprise Security & Resilience](#6-enterprise-security--resilience)
7. [Testing & Quality Gates](#7-testing--quality-gates)

---

## 1. Architecture & Package Structure

```
ge-connectors/
├── ge_connector_tool.py             # Main CLI Entry Point & Multi-Connector Orchestrator
├── config_template.json             # Multi-connector configuration schema and template
├── README.md                        # Package Documentation & User Guide
├── core/
│   ├── catalog.py                   # 61 BAP Actions, Entra ID Least-Privilege Matrix, 33 Engine Features
│   ├── logger.py                    # Redacting logger (scrubs secrets, bearer tokens, passwords)
│   ├── rollback.py                  # Stack-based LIFO Rollback Manager (SIGINT/SIGTERM/Exception)
│   ├── preflight.py                 # Non-destructive Pre-flight Validation Engine
│   └── plugin_base.py               # Abstract Base Class for connector plugins
├── providers/
│   ├── entra_provider.py            # Microsoft Entra ID CLI & API provider, dynamic least privilege
│   └── gcp_provider.py              # Discovery Engine REST API, Engine & Features, Secret Manager (CMEK)
├── plugins/
│   ├── sharepoint.py                # SharePoint Plugin (FEDERATED + DATA_INGESTION, 18 BAP actions)
│   ├── onedrive.py                  # OneDrive Plugin (Personal site resolution, 10 BAP actions)
│   ├── outlook.py                   # Outlook Plugin (Mail, Calendar, Contacts, 21 BAP actions)
│   ├── teams.py                     # Teams Plugin (Team, Channel, Message, File, 12 BAP actions)
│   └── custom_mcp.py                # Custom MCP Server Plugin (Cloud Run URL verification & OAuth)
├── terraform_templates/             # Parameterized Dual-Mode Terraform HCL Modules
│   ├── sharepoint/                  # SharePoint HCL Module (FEDERATED & DATA_INGESTION)
│   ├── onedrive/                    # OneDrive HCL Module
│   ├── outlook/                     # Outlook HCL Module
│   ├── teams/                       # Teams HCL Module
│   ├── custom_mcp/                  # Custom MCP HCL Module
│   └── entra-connector/             # Entra People Data Connector Module
└── tests/                           # Complete Pytest Automated Test Suite
    ├── test_catalog.py              # Tests for actions catalog, scopes, and Engine feature polarity
    ├── test_entra_provider.py       # Tests for requiredResourceAccess payload construction
    ├── test_gcp_provider.py         # Tests for universal BAP connector payload and Engine features
    ├── test_plugins.py              # Tests for plugin validation, entities, and dry-run outputs
    └── test_terraform_generation.py # Tests ensuring all 5 Terraform templates render with 0 tokens
```

---

## 2. Supported Connectors & Architectural Modes

### Supported Connectors

| Connector | Key | Entities Crawled / Queried | BAP Tool Actions | Special Features |
| :--- | :--- | :--- | :---: | :--- |
| **Microsoft SharePoint Online** | `sharepoint` | `file`, `page`, `comment`, `event`, `attachment` | **18 Actions** | Nested site crawling, managed paths, SharePoint API scopes |
| **Microsoft OneDrive** | `onedrive` | `file` | **10 Actions** | Personal site host auto-resolution (`-my.sharepoint.<env>`) |
| **Microsoft Outlook** | `outlook` | `mail`, `mail-attachment`, `calendar`, `contact` | **21 Actions** | Mail sending, drafting, calendar booking, contact management |
| **Microsoft Teams** | `teams` | `team`, `channel`, `channel-message`, `channel-file` | **12 Actions** | Channel messaging, chat threads, shift schedule tools |
| **Custom MCP Server** | `custom_mcp` | Dynamically declared via Model Context Protocol | Extensible | Cloud Run project number URL validation, OAuth token flow |

### Dual Architectural Modes

1. **`FEDERATED` (Default)**:
   - **Real-Time Federated Search & BAP Tool Actions**: `connectorModes = ["FEDERATED", "ACTIONS"]` with `bapConfig.enabledActions`.
   - Allows Gemini Enterprise agents (Agent Builder / Dolphin Runtime) to query live third-party APIs and execute real actions (send emails, create calendar events, upload files, post Teams messages) using end-user delegated OAuth (`3LO`) credentials.
   - Access tier control via `--access-level`: `READ_WRITE` (all 61 tools) or `READ_ONLY` (read-only search tools).

2. **`DATA_INGESTION`**:
   - **Batch Document Indexing**: `connectorModes = ["DATA_CONNECTOR"]` with `aclEnabled = true`.
   - Performs periodic batch crawling of documents and metadata directly into Discovery Engine search index with full Microsoft Entra ID ACL security trimming.

---

## 3. User Guide: Step-by-Step Provisioning & Workflows

### Prerequisites Setup

1. **Google Cloud SDK (`gcloud`)**:
   Authenticate your active Google Cloud session and configure your target project:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_GCP_PROJECT_ID
   ```
   *Required IAM Roles*: `roles/discoveryengine.admin`, `roles/secretmanager.admin`, and `roles/serviceusage.serviceUsageAdmin`.

2. **Azure CLI (`az`)**:
   Authenticate to Microsoft Entra ID without requiring Azure billing subscriptions:
   ```bash
   az login --use-device-code --allow-no-subscriptions
   ```
   *Required Entra ID Role*: `Cloud Application Administrator` (minimum) or `Global Administrator` (for automated background admin consent).

---

### Workflow A: Interactive Terminal Wizard (Quickstart)

If run without arguments (or with `--interactive`), the tool guides you step-by-step with color-coded prompts, input validation, auto-detection of your current environment, and pre-selected intelligent defaults.

1. Launch the interactive wizard:
   ```bash
   python3 ge_connector_tool.py
   ```
2. **Select Connectors**: Choose one or multiple connectors (e.g., `sharepoint`, `onedrive`, `outlook`, `teams`, or `all`).
3. **Select Architecture Mode**: Choose `FEDERATED` (real-time query + actions) or `DATA_INGESTION` (batch crawl + ACLs).
4. **Choose Action Access Tier**: Choose `READ_WRITE` to enable write tools or `READ_ONLY` for search-only.
5. **Confirm Cloud Environment**: Select standard Commercial (`com`) or US Government / GCC High (`us`).
6. **Entra ID App Registration**: The wizard detects whether an app registration exists or creates a new one, generates a 2-year client secret, and sets up least-privilege Graph and SharePoint API permissions.
7. **Secret Vaulting**: The client secret is automatically vaulted in Google Cloud Secret Manager with metadata tags (`expiration_date`, `alert_before_days=30`, `created_by=ge_connector_tool`).
8. **Discovery Engine & Engine Linkage**: The tool constructs the BAP payload, initializes the Data Store, and binds it to your Gemini Enterprise Engine.

---

### Workflow B: Scripted / Non-Interactive Automation

For CI/CD pipelines or hands-free execution, pass all parameters via CLI flags or a JSON configuration file.

#### Example 1: CLI Flags (Multi-Connector Provisioning)
```bash
python3 ge_connector_tool.py \
  --connector sharepoint,onedrive,outlook,teams \
  --mode FEDERATED \
  --access-level READ_WRITE \
  --project my-gcp-project \
  --tenant-id 00000000-0000-0000-0000-000000000000 \
  --engine-id ge-m365-app \
  --engine-features RECOMMENDED
```

#### Example 2: Config File (`config_template.json`)
Create or edit `config_template.json`:
```json
{
  "gcp_project": "my-gcp-project",
  "location": "global",
  "entra_tenant_id": "00000000-0000-0000-0000-000000000000",
  "engine_id": "ge-m365-app",
  "mode": "FEDERATED",
  "access_level": "READ_WRITE",
  "o365_env": "com",
  "sharepoint": {
    "instance_uri": "https://acme.sharepoint.com",
    "datastore_id": "sharepoint-ds"
  },
  "onedrive": {
    "instance_uri": "https://acme-my.sharepoint.com",
    "datastore_id": "onedrive-ds"
  },
  "outlook": {
    "datastore_id": "outlook-ds"
  },
  "teams": {
    "tenant_domain": "acme.onmicrosoft.com",
    "datastore_id": "teams-ds"
  }
}
```
Run the tool non-interactively:
```bash
python3 ge_connector_tool.py --connector sharepoint,onedrive,outlook,teams --config config_template.json
```

---

### Workflow C: Dry-Run / Change Plan Simulation

Before making changes in production or customer environments, use `--dry-run` to simulate execution, validate permissions, and preview exact resource mutations without modifying cloud state:

```bash
python3 ge_connector_tool.py --connector sharepoint,onedrive,outlook,teams --config config_template.json --dry-run
```

The tool will output a detailed change plan showing:
- Active connector mode and BAP tool action count.
- Entra ID app registration plan and required permissions.
- Secret Manager secret ID and CMEK KMS key configuration.
- Target Discovery Engine Data Store ID and Engine binding target.

---

### Workflow D: Terraform Infrastructure as Code (IaC) Export

To provision connectors via Terraform, use the `--terraform` flag. The tool translates your inputs into validated, production-ready Terraform HCL code without touching cloud resources:

```bash
python3 ge_connector_tool.py \
  --connector sharepoint,onedrive,outlook,teams,custom_mcp \
  --config config_template.json \
  --terraform \
  --output-dir terraform_output
```

This generates standalone, modular Terraform projects under `terraform_output/<connector>/`:
- `azuread.tf`: Entra ID Application, Service Principal, and delegated/application API permissions.
- `discovery_engine.tf`: Discovery Engine collection and BAP `setUpDataConnector` API resource with dynamic modes (`FEDERATED` vs `DATA_INGESTION`).
- `gcp_secret_manager.tf`: Secret Manager secret container with CMEK encryption and expiration tags.
- `variables.tf`, `outputs.tf`, `providers.tf`: Provider declarations and variable schemas.
- `terraform.tfvars`: Populated with your exact project, tenant, and connector configuration.

To deploy via Terraform:
```bash
cd terraform_output/sharepoint
terraform init
terraform plan
terraform apply
```

---

### Post-Setup: Admin Consent & Gemini Enterprise Authorization

Once provisioning completes, the tool prints post-setup guidance:

#### 1. Tenant-Wide Admin Consent
- **Global Administrator Session**: Tenant-wide admin consent is automatically granted in the background via Microsoft Graph API.
- **Cloud Application Administrator Session**: If automated consent is skipped due to insufficient directory privileges, an admin can approve permissions directly in the Microsoft Entra Admin Center:
  1. Open: `https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/<CLIENT_ID>`
  2. Click **"Grant admin consent for <tenant>"**.
  3. Confirm that green check marks appear next to the requested scopes.

#### 2. Authorize in Gemini Enterprise Console
To complete the end-user OAuth handshake:
1. Navigate to the Google Cloud Console:
   `https://console.cloud.google.com/gen-app-builder/data-stores?project=YOUR_PROJECT_ID`
2. Select your newly created Data Store (e.g. `sharepoint-ds`).
3. Click the **Authorize** button.
4. Complete the Microsoft 365 sign-in modal.
5. The connector status will transition to **Connected / Active**.

---

## 4. CLI Command-Line Flag Reference

| Flag | Short | Default | Description |
| :--- | :---: | :--- | :--- |
| `--connector` | `-c` | `sharepoint` | Target connector(s): `sharepoint`, `onedrive`, `outlook`, `teams`, `custom_mcp`, `all`, or comma-separated list. |
| `--mode` | `-m` | `FEDERATED` | Architectural mode: `FEDERATED` (real-time query + actions) or `DATA_INGESTION` (batch crawl + ACLs). |
| `--access-level` | | `READ_WRITE` | Action tool permission tier: `READ_WRITE` (all supported tools) or `READ_ONLY` (search tools only). |
| `--engine-features` | | `RECOMMENDED` | Gemini Enterprise Engine features: `RECOMMENDED` (standard apps), `ALL` (all 33 features), or comma-separated keys. |
| `--engine-id` | `-e` | `""` | Gemini Enterprise App/Engine ID to bind the Data Store to. |
| `--o365-env` | | `com` | Microsoft 365 cloud environment TLD suffix: `com` (Commercial), `us` (GCC High), or custom. |
| `--project` | `-p` | Active gcloud | Google Cloud Project ID override. |
| `--location` | `-l` | `global` | Discovery Engine location (`global`, `us`, `eu`). |
| `--tenant-id` | | Active az | Microsoft Entra ID Tenant ID override. |
| `--client-id` | | `""` | Existing Entra ID Application (Client) ID to reuse. |
| `--mcp-url` | | `""` | Custom MCP Server URL (required for `custom_mcp` connector). |
| `--config` | | `""` | Path to JSON configuration file for non-interactive execution. |
| `--dry-run` | | `False` | Simulates execution, validates configuration, and renders change plan. |
| `--terraform` | | `False` | Generates Terraform HCL configuration files instead of directly provisioning. |
| `--output-dir` | | `terraform_output` | Target directory for generated Terraform files. |
| `--verbose` | | `False` | Enables detailed `DEBUG` logging output in console. |

---

## 5. Configuration File Specification (`config_template.json`)

```json
{
  "gcp_project": "my-gcp-project-id",
  "location": "global",
  "entra_tenant_id": "00000000-0000-0000-0000-000000000000",
  "engine_id": "ge-m365-app",
  "existing_client_id": null,
  "cmek_kms_key": null,
  "mode": "FEDERATED",
  "access_level": "READ_WRITE",
  "o365_env": "com",
  "sharepoint": {
    "instance_uri": "https://acme.sharepoint.com",
    "datastore_id": "sharepoint-ds"
  },
  "onedrive": {
    "instance_uri": "https://acme-my.sharepoint.com",
    "datastore_id": "onedrive-ds"
  },
  "outlook": {
    "datastore_id": "outlook-ds"
  },
  "teams": {
    "tenant_domain": "acme.onmicrosoft.com",
    "datastore_id": "teams-ds"
  },
  "custom_mcp": {
    "mcp_url": "https://my-service-12345.us-central1.run.app/mcp",
    "datastore_id": "ms-custom-mcp-connector"
  }
}
```

---

## 6. Enterprise Security & Resilience

1. **Zero-Trust Secret Management**:
   - Client Secrets are never saved to plaintext files on disk.
   - Secrets are vaulted directly into Google Cloud Secret Manager with automatic expiration tags:
     `expiration_date=<date>,connector_type=microsoft_365,alert_before_days=30,created_by=ge_connector_tool`.
   - Supports Customer-Managed Encryption Keys (**CMEK**) using Cloud KMS key rings.

2. **Stack-Based LIFO Rollback (`core/rollback.py`)**:
   - Signal handlers (`SIGINT`, `SIGTERM`, unhandled exceptions) trap runtime aborts.
   - If provisioning fails midway, `RollbackManager` executes recorded undo handlers in reverse order (LIFO), deleting transient Entra ID apps, Secret Manager secrets, and Discovery Engine resources so that half-configured or orphan resources are never left behind.

3. **Log Sanitization (`core/logger.py`)**:
   - The `RedactingFormatter` automatically scrubs Bearer tokens, OAuth client secrets, passwords, and sensitive HTTP headers before writing to stdout or the `ge_connector_setup.log` audit log.

4. **Engine Feature Polarity Management (`core/catalog.py`)**:
   - Manages 33 Gemini Enterprise feature flags with polarity awareness. Flags with negative/inverted keys (`disable-canvas`, `disable-multi-agent-orchestration`, `disable-onedrive-upload`) are properly inverted so that enabling them in the configuration translates to `FEATURE_STATE_OFF` in the API payload.

---

## 7. Testing & Quality Gates

The repository contains an automated test suite verifying catalog definitions, provider payload generation, plugin lifecycle methods, and Terraform template substitution.

To run the complete test suite:
```bash
python3 -m pytest tests/ -v
```

### Test Coverage Summary:
- `tests/test_catalog.py`: Verifies all 61 BAP actions, least-privilege permission matrix, and Engine feature flag polarity.
- `tests/test_entra_provider.py`: Verifies Microsoft Graph and SharePoint `requiredResourceAccess` payload formatting.
- `tests/test_gcp_provider.py`: Verifies BAP `setUpDataConnector` JSON structure in both `FEDERATED` and `DATA_INGESTION` modes.
- `tests/test_plugins.py`: Verifies input validation and dry-run execution for all 5 plugins.
- `tests/test_terraform_generation.py`: Verifies that all 5 Terraform connector templates render cleanly with zero unresolved tokens.
