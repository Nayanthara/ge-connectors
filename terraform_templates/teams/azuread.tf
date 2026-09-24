# Create new Entra ID App Registration for Teams
resource "azuread_application" "teams" {
  count            = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  display_name     = "Gemini-Enterprise-Teams-${var.datastore_id}"
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

    # ChannelMessage.Send (Delegated)
    resource_access {
      id   = "ebf6018b-837d-4eb0-867e-ecd24cb84272"
      type = "Scope"
    }

    # ChannelMessage.Read.All (Delegated)
    resource_access {
      id   = "04c2196d-350e-4364-969c-ea00787e7485"
      type = "Scope"
    }

    # Chat.Read (Delegated)
    resource_access {
      id   = "0e263e50-5827-48a4-b97c-d940288653c7"
      type = "Scope"
    }

    # ChatMessage.Send (Delegated)
    resource_access {
      id   = "81f18579-5095-46a4-bb50-3ee91f24d4d6"
      type = "Scope"
    }

    # Team.ReadBasic.All (Delegated)
    resource_access {
      id   = "b328a6f4-ec01-4475-81d3-3567d2685718"
      type = "Scope"
    }

    # Channel.ReadBasic.All (Role)
    resource_access {
      id   = "24354228-569b-449e-8c82-ef7b337c6883"
      type = "Role"
    }
  }
}

# Service Principal for the App Registration
resource "azuread_service_principal" "teams_sp" {
  count                        = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  client_id                    = azuread_application.teams[0].client_id
  app_role_assignment_required = false
}

# Client Secret for OAuth authentication
resource "azuread_application_password" "teams_secret" {
  count             = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  application_id    = azuread_application.teams[0].id
  display_name      = "Gemini Enterprise Connector Secret"
  end_date_relative = "17520h" # 2 years validity
}

locals {
  effective_client_id = var.existing_client_id != null && var.existing_client_id != "" ? var.existing_client_id : azuread_application.teams[0].client_id
  client_secret_value = var.existing_client_id == null || var.existing_client_id == "" ? azuread_application_password.teams_secret[0].value : ""
}

