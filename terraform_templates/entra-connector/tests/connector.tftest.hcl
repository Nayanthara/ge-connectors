mock_provider "google" {}

variables {
  project_id      = "your-gcp-project-id"
  ge_location     = "global"
  entra_tenant_id = "00000000-0000-0000-0000-000000000000"
  entra_client_id = "00000000-0000-0000-0000-000000000000"
}

run "verify_default_configuration" {
  command = plan

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.data_source == "azure_active_directory"
    error_message = "Data source must be 'azure_active_directory'"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.refresh_interval == "86400s"
    error_message = "Default refresh interval must be '86400s'"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.sync_mode == "PERIODIC"
    error_message = "Sync mode must be 'PERIODIC'"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.auto_run_disabled == false
    error_message = "Auto run should not be disabled by default"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.project == "your-gcp-project-id"
    error_message = "Default project ID must be 'your-gcp-project-id'"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.location == "global"
    error_message = "Default location must be 'global'"
  }

  assert {
    condition     = contains(google_discovery_engine_data_connector.entra_connector_v2.connector_modes, "DATA_INGESTION")
    error_message = "Connector modes must include DATA_INGESTION"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.params["azure_tenant"] == "00000000-0000-0000-0000-000000000000"
    error_message = "Default Azure tenant ID must match dummy placeholder"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.params["client_id"] == "00000000-0000-0000-0000-000000000000"
    error_message = "Default Entra client ID must match dummy placeholder"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.params["max_qps"] == "50"
    error_message = "Max QPS must be configured to 50"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.params["global_custom_sql_filter"] == "accountEnabled = 'true'"
    error_message = "Global custom SQL filter must filter on accountEnabled = 'true'"
  }

  assert {
    condition     = terraform_data.entra_connector_sync_time.triggers_replace.hours == 3
    error_message = "Default sync hours must be 3 for prod environment"
  }

  assert {
    condition     = terraform_data.entra_connector_sync_time.triggers_replace.minutes == 0
    error_message = "Default sync minutes must be 0"
  }

  assert {
    condition     = terraform_data.entra_connector_sync_time.triggers_replace.timezone == "America/New_York"
    error_message = "Sync timezone must be 'America/New_York'"
  }
}

run "verify_custom_inputs" {
  command = plan

  variables {
    project_id      = "custom-test-project"
    ge_location     = "us"
    entra_tenant_id = "11111111-2222-3333-4444-555555555555"
    entra_client_id = "66666666-7777-8888-9999-000000000000"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.project == "custom-test-project"
    error_message = "Custom project ID was not applied to connector"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.location == "us"
    error_message = "Custom location was not applied to connector"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.params["azure_tenant"] == "11111111-2222-3333-4444-555555555555"
    error_message = "Custom Azure tenant ID was not applied to connector"
  }

  assert {
    condition     = google_discovery_engine_data_connector.entra_connector_v2.params["client_id"] == "66666666-7777-8888-9999-000000000000"
    error_message = "Custom Entra client ID was not applied to connector"
  }

  assert {
    condition     = terraform_data.entra_connector_sync_time.triggers_replace.project_id == "custom-test-project"
    error_message = "Custom project ID was not applied to sync time triggers"
  }
}
