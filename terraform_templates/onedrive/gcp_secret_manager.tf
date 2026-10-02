# Enable required Google Cloud APIs
resource "google_project_service" "enabled_apis" {
  for_each = toset([
    "discoveryengine.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com"
  ])

  project            = var.gcp_project
  service            = each.key
  disable_on_destroy = false
}

# GCP Secret Manager Secret Container
resource "google_secret_manager_secret" "oauth_secret" {
  project   = var.gcp_project
  secret_id = "${var.datastore_id}-oauth-secret"

  labels = {
    connector_type    = "sharepoint_federated_search"
    alert_before_days = "30"
  }

  replication {
    dynamic "user_managed" {
      for_each = var.cmek_kms_key != null && var.cmek_kms_key != "" ? [1] : []
      content {
        replicas {
          location = var.gcp_region
          customer_managed_encryption {
            kms_key_name = var.cmek_kms_key
          }
        }
      }
    }

    dynamic "auto" {
      for_each = var.cmek_kms_key == null || var.cmek_kms_key == "" ? [1] : []
      content {}
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

# GCP Secret Manager Secret Version (storing Entra client secret)
resource "google_secret_manager_secret_version" "oauth_secret_version" {
  count       = var.existing_client_id == null || var.existing_client_id == "" ? 1 : 0
  secret      = google_secret_manager_secret.oauth_secret.id
  secret_data = local.client_secret_value
}
