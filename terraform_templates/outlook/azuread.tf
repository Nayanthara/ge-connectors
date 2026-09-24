# Create new Entra ID App Registration for Outlook
resource "azuread_application" "outlook" {
  count            = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  display_name     = "Gemini-Enterprise-Outlook-${var.datastore_id}"
  sign_in_audience = "AzureADMyOrg"

  web {
    redirect_uris = [
      "https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html",
      "https://vertexaisearch.cloud.google.com/oauth-redirect",
      "https://vertexaisearch.cloud.google.com/console/oauth/generic_oauth.html"
    ]
  }

  # Microsoft Graph API (App ID: 00000003-0000-0000-c000-000000000000)
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000"

    # User.Read (Delegated)
    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"
      type = "Scope"
    }

    # Mail.Read (Delegated)
    resource_access {
      id   = "570265a9-50c9-4aa7-Bag9-88c02c98d7ca"
      type = "Scope"
    }

    # Mail.ReadWrite (Delegated)
    resource_access {
      id   = "024d486e-b451-40bb-833d-3e66d9b66f4e"
      type = "Scope"
    }

    # Mail.Send (Delegated)
    resource_access {
      id   = "e383f46e-2787-4529-855e-0e479a3ffac0"
      type = "Scope"
    }

    # Calendars.Read (Delegated)
    resource_access {
      id   = "465a38f9-7676-45ff-aa6b-aac812dd90e8"
      type = "Scope"
    }

    # Calendars.ReadWrite (Delegated)
    resource_access {
      id   = "12466101-c9b8-439a-bf63-8a6f41e574f8"
      type = "Scope"
    }

    # Contacts.Read (Delegated)
    resource_access {
      id   = "ff74d97f-43af-4b68-9f9a-270da074f40f"
      type = "Scope"
    }

    # Contacts.ReadWrite (Delegated)
    resource_access {
      id   = "d56682ec-c09e-4743-aaf4-1a3aac4caa21"
      type = "Scope"
    }
  }
}

# Service Principal for the App Registration
resource "azuread_service_principal" "outlook_sp" {
  count                        = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  client_id                    = azuread_application.outlook[0].client_id
  app_role_assignment_required = false
}

# Client Secret for OAuth authentication
resource "azuread_application_password" "outlook_secret" {
  count             = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  application_id    = azuread_application.outlook[0].id
  display_name      = "Gemini Enterprise Connector Secret"
  end_date_relative = "17520h" # 2 years validity
}

locals {
  effective_client_id = var.existing_client_id != null && var.existing_client_id != "" ? var.existing_client_id : azuread_application.outlook[0].client_id
  client_secret_value = var.existing_client_id == null || var.existing_client_id == "" ? azuread_application_password.outlook_secret[0].value : ""
}

