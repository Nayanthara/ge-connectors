# Data source to obtain GCP OAuth access token for Discovery Engine REST setup
data "google_client_config" "current" {}

# Provision Custom MCP Server Connector in Discovery Engine
# Uses the official setUpDataConnector endpoint:
# https://discoveryengine.googleapis.com/v1alpha/projects/{project}/locations/{location}:setUpDataConnector
resource "terraform_data" "setup_custom_mcp_connector" {
  input = {
    project_id   = var.gcp_project
    location     = var.gcp_location
    datastore_id = var.datastore_id
    mcp_url      = var.mcp_url
    client_id    = local.effective_client_id
    tenant_id    = var.entra_tenant_id
    engine_id    = var.engine_id
  }

  provisioner "local-exec" {
    command = <<EOT
ACCESS_TOKEN="${data.google_client_config.current.access_token}"
if [ -z "$ACCESS_TOKEN" ]; then
  ACCESS_TOKEN=$(gcloud auth print-access-token)
fi

AUTH_URL="https://login.microsoftonline.com/${var.entra_tenant_id}/oauth2/v2.0/authorize"
TOKEN_URL="https://login.microsoftonline.com/${var.entra_tenant_id}/oauth2/v2.0/token"

PAYLOAD=$(cat <<JSON
{
  "collectionId": "${var.datastore_id}",
  "collectionDisplayName": "Microsoft Custom MCP Actions (${var.datastore_id})",
  "dataConnector": {
    "dataSource": "custom_mcp",
    "connectorModes": ["ACTIONS", "FEDERATED"],
    "params": {
      "oauth_access_token": "placeholder"
    },
    "actionConfig": {
      "actionParams": {
        "instance_uri": "${var.mcp_url}",
        "auth_uri": "$AUTH_URL",
        "token_uri": "$TOKEN_URL",
        "client_id": "${local.effective_client_id}",
        "client_secret": "${local.client_secret_value}",
        "scopes": "offline_access .default"
      },
      "createBapConnection": true,
      "isActionConfigured": true
    },
    "refreshInterval": "7200s"
  }
}
JSON
)

curl -s -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${var.gcp_project}" \
  -d "$PAYLOAD" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${var.gcp_project}/locations/${var.gcp_location}:setUpDataConnector"

if [ -n "${var.engine_id}" ]; then
  echo "Binding Data Store to Engine ${var.engine_id}..."
  python3 -c "
import json, urllib.request, urllib.error

url = 'https://discoveryengine.googleapis.com/v1alpha/projects/${var.gcp_project}/locations/${var.gcp_location}/collections/default_collection/engines/${var.engine_id}'
headers = {'Authorization': 'Bearer ' + '$ACCESS_TOKEN', 'X-Goog-User-Project': '${var.gcp_project}'}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    ds_ids = data.get('dataStoreIds', [])
    if '${var.datastore_id}' not in ds_ids:
        ds_ids.append('${var.datastore_id}')
        patch_headers = dict(headers, **{'Content-Type': 'application/json'})
        patch_req = urllib.request.Request(
            url + '?updateMask=dataStoreIds',
            data=json.dumps({'dataStoreIds': ds_ids}).encode('utf-8'),
            headers=patch_headers,
            method='PATCH',
        )
        urllib.request.urlopen(patch_req)
        print('Data Store ${var.datastore_id} successfully bound to Engine ${var.engine_id}.')
    else:
        print('Data Store ${var.datastore_id} is already linked to Engine ${var.engine_id}.')
except urllib.error.HTTPError as e:
    if e.code == 404:
        print('Engine ${var.engine_id} not found. Skipping binding.')
    else:
        print('Engine binding failed (' + str(e.code) + '): ' + e.read().decode('utf-8'))
except Exception as e:
    print('Engine binding skipped: ' + str(e))
"
fi
EOT
  }

  depends_on = [
    google_project_service.enabled_apis,
    google_secret_manager_secret_version.oauth_secret_version,
  ]
}

