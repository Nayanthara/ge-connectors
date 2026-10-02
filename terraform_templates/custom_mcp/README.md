# Terraform Deployment for Gemini Enterprise Custom MCP Connector

This Terraform configuration automates the provisioning of:
1. Microsoft Entra ID (Azure AD) App Registration with delegated `User.Read` permission, and Client Secret for Custom MCP authentication.
2. Google Cloud Platform (GCP) APIs and Secret Manager for OAuth secrets with CMEK support.
3. Gemini Enterprise (Discovery Engine) Custom MCP Federated Action Data Store configured with the target MCP server endpoint URL.

## Prerequisites
- **Terraform CLI** >= 1.5.0
- **Azure CLI (`az`)** authenticated via `az login`
- **Google Cloud SDK (`gcloud`)** authenticated via `gcloud auth login` and `gcloud auth application-default login`
- Active deployed **Custom MCP Server endpoint** (e.g. deployed on Cloud Run)

## Deployment Steps

1. Review and adjust `terraform.tfvars` (or copy from `terraform.tfvars.tpl` if needed), ensuring `mcp_url` is configured.
2. Initialize Terraform:
   ```bash
   terraform init
   ```
3. Preview proposed changes:
   ```bash
   terraform plan
   ```
4. Apply infrastructure:
   ```bash
   terraform apply
   ```

## Admin Consent
After applying, an Entra ID Administrator must grant tenant-wide Admin Consent:
- Open: `https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/<ENTRA_CLIENT_ID>`
- Click **"Grant admin consent for <Tenant>"**.
