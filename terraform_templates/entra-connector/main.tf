resource "google_discovery_engine_data_connector" "entra_connector_v2" {
  project     = var.project_id
  location    = var.ge_location
  data_source = local.ENTRA_DATASOURCE

  collection_id           = local.environment_friendly == local.DEV_ENV ? "${local.ENTRA_COLLECTION_ID}-${random_id.entra_ds_suffix_4.hex}" : "${local.ENTRA_COLLECTION_ID}-${random_id.entra_ds_suffix_prod_2.hex}"
  collection_display_name = local.environment_friendly == local.DEV_ENV ? "People Data (Entra) v2 (${local.environment_friendly})" : local.ENTRA_COLLECTION_DISPLAY_NAME

  refresh_interval  = local.ENTRA_REFRESH_INTERVAL
  connector_modes   = local.ENTRA_CONNECTOR_MODES
  sync_mode         = "PERIODIC"
  auto_run_disabled = local.ENTRA_CONNECTOR_PAUSED

  dynamic "entities" {
    for_each = local.ENTRA_ENTITIES
    content {
      entity_name = entities.value
    }
  }

  params = {
    azure_tenant  = local.ENTRA_TENENT_ID
    client_id     = local.ENTRA_CLIENT_ID
    client_secret = data.google_secret_manager_secret_version.entra_client_secret_latest.secret_data
    max_qps       = "50"
    # Fix: Wrapped the true boolean value in single quotes as expected by the internal schema textproto.
    global_custom_sql_filter = "accountEnabled = 'true'"
  }

  lifecycle {
    ignore_changes = [entities, params]
  }
}

resource "terraform_data" "entra_connector_sync_time" {
  triggers_replace = {
    collection_id = google_discovery_engine_data_connector.entra_connector_v2.collection_id
    project_id    = var.project_id
    hours         = local.ENTRA_SYNC_TIME_HOURS
    minutes       = local.ENTRA_SYNC_TIME_MINUTES
    timezone      = local.ENTRA_SYNC_TIME_TIMEZONE
    version       = 2
  }

  provisioner "local-exec" {
    command = "${path.module}/scripts/update_sync_time.sh"
    environment = {
      GE_LOCATION       = var.ge_location
      PROJECT_NUMBER    = data.google_project.this.number
      PROJECT_ID        = var.project_id
      COLLECTION_ID     = google_discovery_engine_data_connector.entra_connector_v2.collection_id
      ACCESS_TOKEN      = data.google_client_config.current.access_token
      REFRESH_INTERVAL  = local.ENTRA_REFRESH_INTERVAL
      SYNC_TIME_HOURS   = local.ENTRA_SYNC_TIME_HOURS
      SYNC_TIME_MINUTES = local.ENTRA_SYNC_TIME_MINUTES
      SYNC_TIME_TZ      = local.ENTRA_SYNC_TIME_TIMEZONE
    }
  }

  depends_on = [google_discovery_engine_data_connector.entra_connector_v2]
}