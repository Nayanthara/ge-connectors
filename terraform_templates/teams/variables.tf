variable "gcp_project" {
  type        = string
  description = "The GCP Project ID where Gemini Enterprise is configured."
}

variable "gcp_location" {
  type        = string
  description = "The GCP Location for Discovery Engine (e.g. global, us, eu)."
  default     = "global"
}

variable "gcp_region" {
  type        = string
  description = "The default GCP region for regional resources."
  default     = "us-central1"
}

variable "connector_mode" {
  type        = string
  description = "Connector mode: FEDERATED (default) or DATA_INGESTION."
  default     = "FEDERATED"
}

variable "action_access_level" {
  type        = string
  description = "Action access tier: READ_WRITE (default) or READ_ONLY."
  default     = "READ_WRITE"
}

variable "entra_tenant_id" {
  type        = string
  description = "The Microsoft Entra ID (Azure AD) Directory / Tenant ID."
}

variable "tenant_domain" {
  type        = string
  description = "The Microsoft Entra ID Tenant Domain (e.g. acme.onmicrosoft.com)."
  default     = "tenant.onmicrosoft.com"
}

variable "datastore_id" {
  type        = string
  description = "The Discovery Engine Data Store ID to create."
  default     = "teams-ds"
}

variable "engine_id" {
  type        = string
  description = "The Gemini Enterprise Engine/App ID to bind the Data Store to (optional)."
  default     = ""
}

variable "cmek_kms_key" {
  type        = string
  description = "Optional Cloud KMS CryptoKey resource ID for CMEK encryption in Secret Manager."
  default     = null
}

variable "existing_client_id" {
  type        = string
  description = "Optional existing Microsoft Entra ID App Client ID. If omitted, a new App Registration is created."
  default     = null
}

