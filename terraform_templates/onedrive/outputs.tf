output "gcp_project" {
  description = "Target GCP Project ID"
  value       = var.gcp_project
}

output "datastore_id" {
  description = "Provisioned Discovery Engine Data Store ID"
  value       = var.datastore_id
}

output "entra_client_id" {
  description = "Microsoft Entra ID Application Client ID"
  value       = local.effective_client_id
}

output "secret_manager_secret" {
  description = "GCP Secret Manager Secret ID"
  value       = google_secret_manager_secret.oauth_secret.id
}

output "admin_consent_url" {
  description = "Microsoft Entra Admin Center Direct URL to grant Admin Consent"
  value       = "https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/${local.effective_client_id}"
}
