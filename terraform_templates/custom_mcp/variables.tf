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

variable "mcp_url" {
  type        = string
  description = "Custom Model Context Protocol (MCP) server endpoint URL."
}

variable "entra_tenant_id" {
  type        = string
  description = "The Microsoft Entra ID (Azure AD) Directory / Tenant ID."
}

variable "datastore_id" {
  type        = string
  description = "The Discovery Engine Data Store ID to create."
  default     = "ms-custom-mcp-connector"
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

