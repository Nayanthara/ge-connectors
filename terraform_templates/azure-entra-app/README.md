# Terraform Deployment for Microsoft Entra ID App Registration

This Terraform configuration automates the provisioning of:
1. Microsoft Entra ID (Azure AD) Application Registration and Service Principal.
2. Delegated OAuth2 API permissions for Microsoft Graph and SharePoint Online.
3. Client Secret credentials with configurable expiration and rotation.
4. Optional tenant-wide administrator consent automation.

## Prerequisites
- **Terraform CLI** >= 1.5.0
- **Azure CLI (`az`)** authenticated via `az login`
- Appropriate Entra ID Directory role:
  - **Application Administrator** or **Cloud Application Administrator** to create app registrations.
  - **Global Administrator** or **Privileged Role Administrator** if `grant_admin_consent = true`.

## Deployment Steps

1. Populate `terraform.tfvars` from `terraform.tfvars.tpl`:
   ```bash
   cp terraform.tfvars.tpl terraform.tfvars
   ```
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
After applying, an Entra ID Administrator can grant tenant-wide Admin Consent:
- Open: `https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/<ENTRA_CLIENT_ID>`
- Click **"Grant admin consent for <Tenant>"**.

## Outputs

| Output Name | Type | Description |
| :--- | :--- | :--- |
| `tenant_id` | `string` | The Microsoft Entra ID Tenant ID |
| `entra_client_id` | `string` | Microsoft Entra ID Application Client ID |
| `client_id` | `string` | Application (Client) ID |
| `application_object_id` | `string` | Object ID of the App Registration |
| `service_principal_object_id` | `string` | Object ID of the Enterprise Application (Service Principal) |
| `client_secret` | `string` (sensitive) | The generated Client Secret |
| `client_secret_end_date` | `string` | Expiration date of the Client Secret |
| `admin_consent_url` | `string` | Direct Microsoft Entra portal URL to grant Admin Consent |
