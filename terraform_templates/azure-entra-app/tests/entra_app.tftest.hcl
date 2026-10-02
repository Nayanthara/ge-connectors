mock_provider "azuread" {
  mock_data "azuread_service_principal" {
    defaults = {
      object_id = "00000000-0000-0000-0000-000000000001"
      oauth2_permission_scope_ids = {
        "User.Read"        = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"
        "Sites.Search.All" = "1002502a-9a71-4426-8551-69ab83452fab"
        "AllSites.Read"    = "4e0d77b0-96ba-4398-af14-3baa780278f4"
        "Files.Read.All"   = "00000000-0000-0000-0000-000000000003"
      }
    }
  }

  mock_resource "azuread_service_principal" {
    defaults = {
      object_id = "00000000-0000-0000-0000-000000000002"
    }
  }
}

variables {
  app_name            = "SharePoint-Online-Connector-App"
  grant_admin_consent = false
}

run "verify_default_configuration" {
  command = plan

  assert {
    condition     = azuread_application.this.display_name == "SharePoint-Online-Connector-App"
    error_message = "Default app display name must be 'SharePoint-Online-Connector-App'"
  }

  assert {
    condition     = azuread_application.this.sign_in_audience == "AzureADMyOrg"
    error_message = "Sign in audience must be 'AzureADMyOrg'"
  }

  assert {
    condition     = length(azuread_application.this.web[0].redirect_uris) == 2
    error_message = "Expected 2 default redirect URIs"
  }

  assert {
    condition     = length(azuread_application.this.required_resource_access) == 2
    error_message = "Expected 2 required resource access blocks (Graph and SharePoint)"
  }

  assert {
    condition     = length(azuread_service_principal_delegated_permission_grant.msgraph) == 0
    error_message = "Admin consent should be disabled by default"
  }

  assert {
    condition     = length(azuread_service_principal_delegated_permission_grant.sharepoint) == 0
    error_message = "Admin consent should be disabled by default"
  }
}

run "verify_custom_inputs_and_admin_consent" {
  command = plan

  variables {
    app_name                     = "Custom-SharePoint-App"
    sign_in_audience             = "AzureADMultipleOrgs"
    redirect_uris                = ["https://example.com/oauth/callback"]
    client_secret_rotation_hours = "4380h"
    grant_admin_consent          = true
    graph_scopes                 = ["User.Read"]
    sharepoint_scopes            = ["Sites.Search.All"]
  }

  assert {
    condition     = azuread_application.this.display_name == "Custom-SharePoint-App"
    error_message = "Custom app name was not applied"
  }

  assert {
    condition     = azuread_application.this.sign_in_audience == "AzureADMultipleOrgs"
    error_message = "Custom sign_in_audience was not applied"
  }

  assert {
    condition     = azuread_application.this.web[0].redirect_uris == toset(["https://example.com/oauth/callback"])
    error_message = "Custom redirect_uris were not applied"
  }

  assert {
    condition     = length(azuread_service_principal_delegated_permission_grant.msgraph) == 1
    error_message = "Graph admin consent grant was not enabled"
  }

  assert {
    condition     = azuread_service_principal_delegated_permission_grant.msgraph[0].claim_values == toset(["User.Read"])
    error_message = "Graph claim_values did not match custom scopes"
  }

  assert {
    condition     = length(azuread_service_principal_delegated_permission_grant.sharepoint) == 1
    error_message = "SharePoint admin consent grant was not enabled"
  }

  assert {
    condition     = azuread_service_principal_delegated_permission_grant.sharepoint[0].claim_values == toset(["Sites.Search.All"])
    error_message = "SharePoint claim_values did not match custom scopes"
  }
}
