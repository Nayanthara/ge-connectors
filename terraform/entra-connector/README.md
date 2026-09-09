# Entra Data Connector Terraform Configuration

Provisions and configures the Google Discovery Engine Microsoft Entra ID (Azure AD) People Data Connector and schedules its synchronization window.

## Prerequisites

### 1. Required GCP APIs
Enable the following APIs in your GCP project:
- **Discovery Engine API** (`discoveryengine.googleapis.com`)
- **Secret Manager API** (`secretmanager.googleapis.com`)
- **Cloud Resource Manager API** (`cloudresourcemanager.googleapis.com`)

```bash
gcloud services enable \
  discoveryengine.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project="<YOUR_PROJECT_ID>"
```

### 2. Secret Manager Secret
Store the Entra application client secret in Secret Manager with the name `entra_client_secret_latest`:
```bash
gcloud secrets create entra_client_secret_latest \
  --data-file=/path/to/client_secret.txt \
  --project="<YOUR_PROJECT_ID>"
```

### 3. Local Tooling & Authentication
- **Terraform** >= 1.0.0
- **gcloud CLI** authenticated:
  ```bash
  gcloud auth application-default login
  ```
- **CLI tools**: `curl` and `jq` (required by `scripts/update_sync_time.sh` during post-provisioning)

## Configuration

1. **Variables (`terraform.tfvars`)**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```
   Set `project_id` and `ge_location` (e.g. `global`, `us`, `eu`).

2. **Connector Settings (`variables.tf`)**:
   Update the `locals` block in `variables.tf` with your environment values:
   - `ENTRA_TENENT_ID`: Entra / Azure AD Directory (tenant) ID.
   - `ENTRA_CLIENT_ID`: Entra Application (client) ID.
   - `environment_friendly`: Target environment (`"dev"` or `"prod"`), which controls collection naming and default sync timing.
   - `ENTRA_SYNC_TIME_HOURS`: Sync start hour (defaults: 5 AM for dev, 3 AM for prod).

3. **Provider Region (`providers.tf`)**:
   Update `region` (defaults to `us-central1`) if needed.

## Deployment

```bash
terraform init
terraform plan
terraform apply
```
