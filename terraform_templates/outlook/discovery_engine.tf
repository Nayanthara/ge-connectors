# Data source to obtain GCP OAuth access token for Discovery Engine REST setup
data "google_client_config" "current" {}

# Provision Outlook Data Connector in Discovery Engine
# Uses the official setUpDataConnector endpoint:
# https://discoveryengine.googleapis.com/v1alpha/projects/{project}/locations/{location}:setUpDataConnector
resource "terraform_data" "setup_outlook_connector" {
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

if [ "${var.connector_mode}" = "DATA_INGESTION" ]; then
  PAYLOAD=$(cat <<JSON
{
  "collectionId": "${var.datastore_id}",
  "collectionDisplayName": "Microsoft Outlook (${var.datastore_id})",
  "dataConnector": {
    "dataSource": "outlook",
    "connectorModes": ["DATA_CONNECTOR"],
    "aclEnabled": true,
    "params": {
      "client_id": "${local.effective_client_id}",
      "client_secret": "${local.client_secret_value}",
      "instance_id": "${var.entra_tenant_id}"
    },
    "actionConfig": {
      "actionParams": {
        "client_id": "${local.effective_client_id}",
        "client_secret": "${local.client_secret_value}",
        "instance_id": "${var.entra_tenant_id}",
        "o365_environment_type": "${var.o365_env}",
        "azure_tenant": "common"
      },
      "createBapConnection": true,
      "isActionConfigured": true
    },
    "bapConfig": {
      "supportedConnectorModes": ["ACTIONS"]
    },
    "entities": [
      {"entityName": "mail"},
      {"entityName": "mail-attachment"},
      {"entityName": "calendar"},
      {"entityName": "contact"}
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
  "collectionDisplayName": "Microsoft Outlook (${var.datastore_id})",
  "dataConnector": {
    "dataSource": "outlook",
    "connectorModes": ["FEDERATED", "ACTIONS"],
    "aclEnabled": false,
    "params": {
      "client_id": "${local.effective_client_id}",
      "client_secret": "${local.client_secret_value}",
      "instance_id": "${var.entra_tenant_id}"
    },
    "actionConfig": {
      "actionParams": {
        "client_id": "${local.effective_client_id}",
        "client_secret": "${local.client_secret_value}",
        "instance_id": "${var.entra_tenant_id}",
        "o365_environment_type": "${var.o365_env}",
        "azure_tenant": "common"
      },
      "createBapConnection": true,
      "isActionConfigured": true
    },
    "bapConfig": {
      "supportedConnectorModes": ["ACTIONS"],
      "enabledActions": [
        "send_mail", "forward_mail", "move_mail", "add_attachments", "download_attachments",
        "create_event", "update_event", "rsvp_to_event", "create_calendar", "update_calendar",
        "create_contact", "update_contact", "word_create_document", "word_convert_to_pdf",
        "pptx_create_presentation", "pptx_convert_to_pdf", "excel_create_table",
        "excel_create_worksheet", "excel_add_row_to_table", "excel_update_row", "excel_add_key_column"
      ]
    },
    "entities": [
      {"entityName": "mail"},
      {"entityName": "mail-attachment"},
      {"entityName": "calendar"},
      {"entityName": "contact"}
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
  curl -s -X POST \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "X-Goog-User-Project: ${var.gcp_project}" \
    "https://discoveryengine.googleapis.com/v1alpha/projects/${var.gcp_project}/locations/${var.gcp_location}/collections/default_collection/engines/${var.engine_id}/dataStores?dataStoreId=${var.datastore_id}"
fi
EOT
  }

  depends_on = [
    google_project_service.enabled_apis,
    google_secret_manager_secret_version.oauth_secret_version,
  ]
}

