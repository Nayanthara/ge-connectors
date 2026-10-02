entra_tenant_id              = "__ENTRA_TENANT_ID__"
app_name                     = "__APP_NAME__"
sign_in_audience             = "AzureADMyOrg"
client_secret_rotation_hours = "8760h"
grant_admin_consent          = false

# Application IDs for Microsoft APIs
graph_app_id      = "00000003-0000-0000-c000-000000000000"
sharepoint_app_id = "00000003-0000-0ff1-ce00-000000000000"

redirect_uris = [
  "https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html",
  "https://vertexaisearch.cloud.google.com/oauth-redirect"
]

# Delegated permission scopes (human-readable names)
graph_scopes = [
  "User.Read"
]

sharepoint_scopes = [
  "Sites.Search.All",
  "AllSites.Read"
]
