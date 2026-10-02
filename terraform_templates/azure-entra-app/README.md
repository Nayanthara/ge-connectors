# Microsoft Entra ID App Registration Terraform Module

Terraform configuration to register and configure a Microsoft Entra ID (formerly Azure Active Directory) Application with delegated permissions for Microsoft Graph and SharePoint Online, provision a service principal, mint client secrets, and optionally grant tenant-wide administrator consent.

This module is a pure Azure Infrastructure-as-Code implementation of the logic originally in [`providers/entra_provider.py`](../../providers/entra_provider.py).

## Prerequisites

- **Terraform** >= 1.5.0
- **Azure CLI** (`az`) installed and authenticated:
  ```bash
  source ../../.venv/bin/activate # if using virtual environment
  az login
  ```
  *(Or configure Azure Service Principal environment variables: `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`)*
- Appropriate Azure AD / Entra ID directory role:
  - **Application Administrator** or **Cloud Application Administrator** to create app registrations and generate client secrets.
  - **Global Administrator** or **Privileged Role Administrator** if `grant_admin_consent = true`.

## Permissions Configured

The application is provisioned with the following delegated OAuth2 permissions:
- **Microsoft Graph** (`00000003-0000-0000-c000-000000000000`):
  - `User.Read` (`e1fe6dd8-ba31-4d61-89e7-88639da4683d`): Sign in and read user profile
- **Office 365 SharePoint Online** (`00000003-0000-0ff1-ce00-000000000000`):
  - `Sites.Search.All` (`1002502a-9a71-4426-8551-69ab83452fab`): Run search queries across SharePoint sites
  - `AllSites.Read` (`4e0d77b0-96ba-4398-af14-3baa780278f4`): Read items in SharePoint site collections

## Usage

1. Copy the sample variables:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Customize `terraform.tfvars`:
   ```hcl
   app_name                     = "SharePoint-Online-Connector-App"
   sign_in_audience             = "AzureADMyOrg"
   client_secret_rotation_hours = "8760h"
   grant_admin_consent          = false

   # API Application IDs (defaults to standard Microsoft well-known IDs)
   graph_app_id      = "00000003-0000-0000-c000-000000000000"
   sharepoint_app_id = "00000003-0000-0ff1-ce00-000000000000"

   redirect_uris = [
     "https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html",
     "https://vertexaisearch.cloud.google.com/oauth-redirect"
   ]

   graph_scopes = [
     "User.Read"
   ]

   sharepoint_scopes = [
     "Sites.Search.All",
     "AllSites.Read"
   ]
   ```

3. Initialize, validate, and test:
   ```bash
   terraform init
   terraform validate
   terraform test
   ```

4. Deploy:
   ```bash
   terraform plan
   terraform apply
   ```

## Admin Consent Guidance

If `grant_admin_consent` is set to `false` (default) or the deployer is not a Global Administrator:
1. Open the [Microsoft Entra Admin Center](https://entra.microsoft.com).
2. Navigate to **Identity > Applications > App registrations > All applications**.
3. Select your application, click **API permissions**, and click **Grant admin consent for <Tenant>**.

## Outputs

| Output Name | Type | Description |
| :--- | :--- | :--- |
| `tenant_id` | `string` | The Microsoft Entra ID Tenant ID |
| `client_id` | `string` | Application (Client) ID |
| `application_object_id` | `string` | Object ID of the App Registration |
| `service_principal_object_id` | `string` | Object ID of the Enterprise Application (Service Principal) |
| `client_secret` | `string` (sensitive) | The generated Client Secret |
| `client_secret_end_date` | `string` | Expiration date of the Client Secret |
