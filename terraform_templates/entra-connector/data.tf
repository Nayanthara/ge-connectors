data "google_project" "this" {
  project_id = var.project_id
}

data "google_client_config" "current" {}

data "google_secret_manager_secret_version" "entra_client_secret_latest" {
  secret  = "entra_client_secret_latest"
  project = var.project_id
}

resource "random_id" "entra_ds_suffix_4" {
  byte_length = 2
}

resource "random_id" "entra_ds_suffix_prod_2" {
  byte_length = 2
}
