variable "project_id" {
  type        = string
  description = "The GCP Project ID where Discovery Engine and secret manager are located."
  default     = "fde-onboarding-501718"
}

variable "ge_location" {
  type        = string
  description = "The Google Discovery Engine location (e.g., 'global', 'us', 'eu')."
  default     = "global"
}

locals {
  # Environment configuration
  environment_friendly = "prod" # Options: "dev", "prod"
  DEV_ENV              = "dev"

  # Entra Data Source & Collection configuration
  ENTRA_DATASOURCE              = "azure_active_directory"
  ENTRA_COLLECTION_ID           = "entra-people-collection"
  ENTRA_COLLECTION_DISPLAY_NAME = "People Data Connector (Entra) v2 (Prod)"

  # Connector execution configuration
  ENTRA_REFRESH_INTERVAL = "86400s"
  ENTRA_CONNECTOR_MODES  = ["DATA_INGESTION"]
  ENTRA_CONNECTOR_PAUSED = false
  ENTRA_ENTITIES         = ["Userprofiles"]

  # Entra Credentials / Identifiers
  ENTRA_TENENT_ID = "0ad7673e-3c52-47a2-a014-2eb596bb6103"
  ENTRA_CLIENT_ID = "2307c37e-1a37-446f-9b53-0becf0d22486"

  # Sync Schedule
  ENTRA_SYNC_TIME_HOURS    = local.environment_friendly == local.DEV_ENV ? 5 : 3
  ENTRA_SYNC_TIME_MINUTES  = 0
  ENTRA_SYNC_TIME_TIMEZONE = "America/New_York"
}
