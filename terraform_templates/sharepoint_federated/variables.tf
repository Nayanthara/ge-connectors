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
  default     = "sharepoint-federated-ds"
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
