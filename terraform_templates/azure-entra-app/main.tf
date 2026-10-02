data "azuread_client_config" "current" {}

data "azuread_service_principal" "msgraph" {
  client_id = var.graph_app_id
}

data "azuread_service_principal" "sharepoint" {
  client_id = var.sharepoint_app_id
}

resource "azuread_application" "this" {
  display_name     = var.app_name
  sign_in_audience = var.sign_in_audience

  web {
    redirect_uris = var.redirect_uris
  }

  # Dynamically configure Microsoft Graph delegated permission scopes
  dynamic "required_resource_access" {
    for_each = length(var.graph_scopes) > 0 ? [1] : []
    content {
      resource_app_id = data.azuread_service_principal.msgraph.client_id

      dynamic "resource_access" {
        for_each = var.graph_scopes
        content {
          id   = data.azuread_service_principal.msgraph.oauth2_permission_scope_ids[resource_access.value]
          type = "Scope"
        }
      }
    }
  }

  # Dynamically configure SharePoint Online delegated permission scopes
  dynamic "required_resource_access" {
    for_each = length(var.sharepoint_scopes) > 0 ? [1] : []
    content {
      resource_app_id = data.azuread_service_principal.sharepoint.client_id

      dynamic "resource_access" {
        for_each = var.sharepoint_scopes
        content {
          id   = data.azuread_service_principal.sharepoint.oauth2_permission_scope_ids[resource_access.value]
          type = "Scope"
        }
      }
    }
  }
}

resource "azuread_service_principal" "this" {
  client_id    = azuread_application.this.client_id
  use_existing = true
}

resource "azuread_application_password" "this" {
  application_id = azuread_application.this.id
  display_name   = "Terraform Managed Secret"
  end_date       = timeadd(timestamp(), var.client_secret_rotation_hours)

  lifecycle {
    ignore_changes = [end_date]
  }
}

# Optional tenant-wide admin consent for Microsoft Graph scopes
resource "azuread_service_principal_delegated_permission_grant" "msgraph" {
  count                                = var.grant_admin_consent && length(var.graph_scopes) > 0 ? 1 : 0
  service_principal_object_id          = azuread_service_principal.this.object_id
  resource_service_principal_object_id = data.azuread_service_principal.msgraph.object_id
  claim_values                         = var.graph_scopes
}

# Optional tenant-wide admin consent for SharePoint Online scopes
resource "azuread_service_principal_delegated_permission_grant" "sharepoint" {
  count                                = var.grant_admin_consent && length(var.sharepoint_scopes) > 0 ? 1 : 0
  service_principal_object_id          = azuread_service_principal.this.object_id
  resource_service_principal_object_id = data.azuread_service_principal.sharepoint.object_id
  claim_values                         = var.sharepoint_scopes
}
