# Terraform Deployment for Gemini Enterprise 3P Connector

This Terraform configuration automates the provisioning of:
1. Microsoft Entra ID (Azure AD) App Registration, delegated SharePoint permissions, and Client Secret.
2. Google Cloud Platform (GCP) APIs and Secret Manager for OAuth secrets.
3. Gemini Enterprise (Discovery Engine) SharePoint Online Federated Search Data Store.

## Prerequisites
- **Terraform CLI** >= 1.5.0
- **Azure CLI (`az`)** authenticated via `az login`
- **Google Cloud SDK (`gcloud`)** authenticated via `gcloud auth login` and `gcloud auth application-default login`

## Deployment Steps

1. Review and adjust `terraform.tfvars` if needed.
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
