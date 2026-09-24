# Create new Entra ID App Registration if existing_client_id is not provided
resource "azuread_application" "sharepoint" {
  count            = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  display_name     = "Gemini-Enterprise-SharePoint-${var.datastore_id}"
  sign_in_audience = "AzureADMyOrg"

  web {
    redirect_uris = [
      "https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html",
      "https://vertexaisearch.cloud.google.com/oauth-redirect",
      "https://vertexaisearch.cloud.google.com/console/oauth/generic_oauth.html"
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

    # AllSites.Read (Delegated)
    resource_access {
      id   = "57c7b80a-9d90-4131-b844-f852b7573f08"
      type = "Scope"
    }

    # AllSites.Write (Delegated)
    resource_access {
      id   = "8df90b63-00f8-45be-b94f-0dfa1ef37d1e"
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

    # Sites.Read.All (Delegated)
    resource_access {
      id   = "205e70e5-aba6-4c52-a976-6d2d46c48043"
      type = "Scope"
    }

    # Sites.ReadWrite.All (Delegated)
    resource_access {
      id   = "89fe6a52-be36-487e-b7d8-d061c452a0e9"
      type = "Scope"
    }

    # Files.Read.All (Delegated)
    resource_access {
      id   = "10465720-29dd-4523-a11a-6a75c743c9d9"
      type = "Scope"
    }

    # Files.ReadWrite (Delegated)
    resource_access {
      id   = "54472324-9924-4331-a8cf-3de4c795b325"
      type = "Scope"
    }
  }
}

# Service Principal for the App Registration
resource "azuread_service_principal" "sharepoint_sp" {
  count                        = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  client_id                    = azuread_application.sharepoint[0].client_id
  app_role_assignment_required = false
}

# Client Secret for OAuth authentication
resource "azuread_application_password" "sharepoint_secret" {
  count             = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  application_id    = azuread_application.sharepoint[0].id
  display_name      = "Gemini Enterprise Connector Secret"
  end_date_relative = "17520h" # 2 years validity
}

locals {
  effective_client_id = var.existing_client_id != null && var.existing_client_id != "" ? var.existing_client_id : azuread_application.sharepoint[0].client_id
  client_secret_value = var.existing_client_id == null || var.existing_client_id == "" ? azuread_application_password.sharepoint_secret[0].value : ""
}

