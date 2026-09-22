# Create new Entra ID App Registration if existing_client_id is not provided
resource "azuread_application" "sharepoint_federated" {
  count            = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  display_name     = "Gemini-Enterprise-SharePoint-${var.datastore_id}"
  sign_in_audience = "AzureADMyOrg"

  web {
    redirect_uris = [
      "https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html",
      "https://vertexaisearch.cloud.google.com/oauth-redirect"
    ]
  }

  # Office 365 SharePoint Online API (App ID: 00000003-0000-0ff1-ce00-000000000000)
  required_resource_access {
    resource_app_id = "00000003-0000-0ff1-ce00-000000000000"

    # Sites.Search.All (Delegated)
    resource_access {
      id   = "1002502a-9a71-4426-8551-69ab83452fab"
      type = "Scope"
    }

    # Sites.Read.All (Delegated)
    resource_access {
      id   = "4e0d77b0-96ba-4398-af14-3baa780278f4"
      type = "Scope"
    }
  }

  # Microsoft Graph API (App ID: 00000003-0000-0000-c000-000000000000)
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000"

    # User.Read (Delegated)
    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"
      type = "Scope"
    }
  }
}

# Service Principal for the App Registration
resource "azuread_service_principal" "sharepoint_sp" {
  count                        = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  client_id                    = azuread_application.sharepoint_federated[0].client_id
  app_role_assignment_required = false
}

# Client Secret for OAuth authentication
resource "azuread_application_password" "sharepoint_secret" {
  count             = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  application_id    = azuread_application.sharepoint_federated[0].id
  display_name      = "Gemini Enterprise Connector Secret"
  end_date_relative = "8760h" # 1 year validity
}

locals {
  effective_client_id = var.existing_client_id != null && var.existing_client_id != "" ? var.existing_client_id : azuread_application.sharepoint_federated[0].client_id
  client_secret_value = var.existing_client_id == null || var.existing_client_id == "" ? azuread_application_password.sharepoint_secret[0].value : ""
}
