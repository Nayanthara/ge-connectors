variable "app_name" {
  type        = string
  description = "Display name for the Entra ID Application Registration"
  default     = "SharePoint-Online-Connector-App"
}

variable "sign_in_audience" {
  type        = string
  description = "The Microsoft account types that have access to this application (e.g., AzureADMyOrg, AzureADMultipleOrgs, AzureADandPersonalMicrosoftAccount)"
  default     = "AzureADMyOrg"
}

variable "redirect_uris" {
  type        = list(string)
  description = "Allowed web OAuth redirect URIs"
  default = [
    "https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html",
    "https://vertexaisearch.cloud.google.com/oauth-redirect"
  ]
}

variable "graph_app_id" {
  type        = string
  description = "Application (client) ID for Microsoft Graph API"
  default     = "00000003-0000-0000-c000-000000000000"
}

variable "sharepoint_app_id" {
  type        = string
  description = "Application (client) ID for Office 365 SharePoint Online API"
  default     = "00000003-0000-0ff1-ce00-000000000000"
}

variable "graph_scopes" {
  type        = list(string)
  description = "List of delegated Microsoft Graph permission scopes to request (e.g. ['User.Read'])"
  default     = ["User.Read"]
}

variable "sharepoint_scopes" {
  type        = list(string)
  description = "List of delegated SharePoint Online permission scopes to request (e.g. ['Sites.Search.All', 'AllSites.Read'])"
  default     = ["Sites.Search.All", "AllSites.Read"]
}

variable "client_secret_rotation_hours" {
  type        = string
  description = "Relative expiration duration for the client secret (default is 1 year = 8760h)"
  default     = "8760h"
}

variable "grant_admin_consent" {
  type        = bool
  description = "Whether to automatically grant tenant-wide admin consent for delegated permissions (requires Global Admin / Privileged Role Admin)"
  default     = false
}
