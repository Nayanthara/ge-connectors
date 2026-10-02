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

variable "o365_env" {
  type        = string
  description = "Microsoft 365 cloud environment (com or us)."
  default     = "com"
}

variable "entra_tenant_id" {
  type        = string
  description = "The Microsoft Entra ID (Azure AD) Directory / Tenant ID."
}

variable "instance_uri" {
  type        = string
  description = "The SharePoint Online Instance URL (e.g. https://acme.sharepoint.com)."
}

variable "datastore_id" {
  type        = string
  description = "The Discovery Engine Data Store ID to create."
  default     = "sharepoint-ds"
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

