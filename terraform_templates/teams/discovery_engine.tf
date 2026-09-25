# Data source to obtain GCP OAuth access token for Discovery Engine REST setup
data "google_client_config" "current" {}

# Provision Teams Data Connector in Discovery Engine
# Uses the official setUpDataConnector endpoint:
# https://discoveryengine.googleapis.com/v1alpha/projects/{project}/locations/{location}:setUpDataConnector
resource "terraform_data" "setup_teams_connector" {
  input = {
    project_id   = var.gcp_project
    location     = var.gcp_location
    datastore_id = var.datastore_id
    client_id    = local.effective_client_id
    tenant_id    = var.entra_tenant_id
    engine_id    = var.engine_id
    mode         = var.connector_mode
  }

  provisioner "local-exec" {
    command = <<EOT
ACCESS_TOKEN="${data.google_client_config.current.access_token}"
if [ -z "$ACCESS_TOKEN" ]; then
  ACCESS_TOKEN=$(gcloud auth print-access-token)
fi

DOMAIN_URL="https://${var.tenant_domain}"

if [ "${var.connector_mode}" = "DATA_INGESTION" ]; then
  PAYLOAD=$(cat <<JSON
{
  "collectionId": "${var.datastore_id}",
  "collectionDisplayName": "Microsoft Teams (${var.datastore_id})",
  "dataConnector": {
    "dataSource": "teams",
    "connectorModes": ["DATA_CONNECTOR"],
    "aclEnabled": true,
    "params": {
      "client_id": "${local.effective_client_id}",
      "client_secret": "${local.client_secret_value}",
      "instance_id": "${var.entra_tenant_id}",
      "domain_url": "$DOMAIN_URL"
    },
    "actionConfig": {
      "actionParams": {
        "client_id": "${local.effective_client_id}",
        "client_secret": "${local.client_secret_value}",
        "instance_id": "${var.entra_tenant_id}",
        "azure_tenant": "common",
        "include_all_groups": true,
        "include_all_users": true
      },
      "createBapConnection": true,
      "isActionConfigured": true
    },
    "bapConfig": {
      "supportedConnectorModes": ["ACTIONS"]
    },
    "entities": [
      {"entityName": "team"},
      {"entityName": "channel"},
      {"entityName": "channel-message"},
      {"entityName": "channel-file"}
    ],
    "refreshInterval": "7200s",
    "syncMode": "PERIODIC"
  }
}
JSON
)
else
  PAYLOAD=$(cat <<JSON
{
  "collectionId": "${var.datastore_id}",
  "collectionDisplayName": "Microsoft Teams (${var.datastore_id})",
  "dataConnector": {
    "dataSource": "teams",
    "connectorModes": ["FEDERATED", "ACTIONS"],
    "aclEnabled": false,
    "params": {
      "client_id": "${local.effective_client_id}",
      "client_secret": "${local.client_secret_value}",
      "instance_id": "${var.entra_tenant_id}",
      "domain_url": "$DOMAIN_URL"
    },
    "actionConfig": {
      "actionParams": {
        "client_id": "${local.effective_client_id}",
        "client_secret": "${local.client_secret_value}",
        "instance_id": "${var.entra_tenant_id}",
        "azure_tenant": "common",
        "include_all_groups": true,
        "include_all_users": true
      },
      "createBapConnection": true,
      "isActionConfigured": true
    },
    "bapConfig": {
      "supportedConnectorModes": ["ACTIONS"],
      "enabledActions": [
        "send_channel_message", "update_channel_message", "send_chat_message",
        "update_chat_message", "create_channel", "update_channel", "add_member_to_channel",
        "create_chat", "update_chat", "create_schedule", "create_time_off_entry", "update_time_off_entry"
      ]
    },
    "entities": [
      {"entityName": "team"},
      {"entityName": "channel"},
      {"entityName": "channel-message"},
      {"entityName": "channel-file"}
    ],
    "refreshInterval": "7200s",
    "syncMode": "PERIODIC"
  }
}
JSON
)
fi

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

