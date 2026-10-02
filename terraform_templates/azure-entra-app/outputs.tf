output "tenant_id" {
  description = "Active Microsoft Entra ID Tenant ID"
  value       = data.azuread_client_config.current.tenant_id
}

output "client_id" {
  description = "Entra ID App Registration Client ID (Application ID)"
  value       = azuread_application.this.client_id
}

output "application_object_id" {
  description = "Entra ID Application Object ID"
  value       = azuread_application.this.object_id
}

output "service_principal_object_id" {
  description = "Entra ID Service Principal Object ID"
  value       = azuread_service_principal.this.object_id
}

output "entra_client_id" {
  description = "Microsoft Entra ID Application Client ID"
  value       = azuread_application.this.client_id
}

output "client_secret" {
  description = "Generated Client Secret"
  value       = azuread_application_password.this.value
  sensitive   = true
}

output "client_secret_end_date" {
  description = "Client Secret expiration timestamp"
  value       = azuread_application_password.this.end_date
}

output "admin_consent_url" {
  description = "Microsoft Entra Admin Center Direct URL to grant Admin Consent"
  value       = "https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/${azuread_application.this.client_id}"
}
