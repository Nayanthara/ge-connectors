# Data source to obtain GCP OAuth access token for Discovery Engine REST setup
data "google_client_config" "current" {}

# Provision SharePoint Online Federated Data Connector in Discovery Engine
# Uses the official setUpDataConnector endpoint:
# https://discoveryengine.googleapis.com/v1alpha/projects/{project}/locations/{location}:setUpDataConnector
resource "terraform_data" "setup_sharepoint_connector" {
  input = {
    project_id   = var.gcp_project
    location     = var.gcp_location
    datastore_id = var.datastore_id
    instance_uri = var.instance_uri
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

PAYLOAD=$(cat <<JSON
{
  "collectionId": "${var.datastore_id}",
  "collectionDisplayName": "SharePoint Online Federated",
  "dataConnector": {
    "dataSource": "sharepoint_federated_search",
    "params": {
      "client_id": "${local.effective_client_id}",
      "client_secret": "${local.client_secret_value}",
      "instance_uri": "${var.instance_uri}",
      "tenant_id": "${var.entra_tenant_id}"
    },
    "entities": [{"entityName": "file"}],
    "refreshInterval": "7200s",
    "connectorType": "THIRD_PARTY_FEDERATED",
    "connectorModes": ["FEDERATED"]
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
