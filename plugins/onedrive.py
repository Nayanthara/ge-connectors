"""Microsoft OneDrive Data Connector Plugin for Gemini Enterprise.

Automates end-to-end setup for Microsoft OneDrive in both:
- FEDERATED mode (real-time query + 10 BAP tool actions)
- DATA_INGESTION mode (batch crawling and Entra ID ACL trimming)
"""

import json
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from core.catalog import resolve_enabled_actions
from core.plugin_base import BaseConnectorPlugin


class OneDrivePlugin(BaseConnectorPlugin):
  """Connector plugin for Microsoft OneDrive."""

  @property
  def name(self) -> str:
    return "Microsoft OneDrive"

  @property
  def connector_type(self) -> str:
    return "onedrive"

  def prompt_config_interactive(
      self, defaults: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Prompt admin interactively for setup choices with sensible defaults."""
    print("\n\033[1m\033[95m=== ONEDRIVE CONNECTOR CONFIGURATION ===\033[0m")

    # 1. GCP Project ID
    default_project = defaults.get("gcp_project", "")
    project_prompt = (
        f"Enter GCP Project ID [{default_project}]"
        if default_project
        else "Enter GCP Project ID"
    )
    project_id = input(f"{project_prompt}: ").strip() or default_project
    while not project_id:
      project_id = input("GCP Project ID cannot be empty: ").strip()

    # 2. GCP Location
    location = input("Enter GCP Location [default: global]: ").strip() or "global"

    # 3. Connector Mode
    mode_input = input("Enter Connector Mode (FEDERATED/DATA_INGESTION) [default: FEDERATED]: ").strip().upper() or "FEDERATED"
    mode = "DATA_INGESTION" if mode_input.startswith("DATA") else "FEDERATED"

    # 4. Action Access Level
    access_level = "READ_WRITE"
    if mode == "FEDERATED":
      lvl_input = input("Enter Action Level (READ_WRITE/READ_ONLY) [default: READ_WRITE]: ").strip().upper() or "READ_WRITE"
      access_level = "READ_ONLY" if lvl_input.startswith("READ_O") else "READ_WRITE"

    # 5. Environment Type
    o365_env = input("Enter O365 Environment Type (com/us) [default: com]: ").strip().lower() or "com"

    # 6. Entra Tenant ID & Domain
    default_tenant = defaults.get("entra_tenant_id", "")
    tenant_prompt = (
        f"Enter Entra Tenant ID [{default_tenant}]"
        if default_tenant
        else "Enter Entra Tenant ID"
    )
    tenant_id = input(f"{tenant_prompt}: ").strip() or default_tenant
    while not tenant_id:
      tenant_id = input("Entra Tenant ID cannot be empty: ").strip()

    tenant_domain = input("Enter Tenant Domain (e.g. acme.onmicrosoft.com): ").strip()
    prefix = tenant_domain.split(".")[0] if tenant_domain else "myorg"
    default_url = f"https://{prefix}-my.sharepoint.{o365_env}"

    instance_uri = input(f"Enter OneDrive Personal Site URL [{default_url}]: ").strip() or default_url

    # 7. App Registration Choice
    app_choice = (
        input("Create a new Entra ID App Registration? (y/n) [default: y]: ")
        .strip()
        .lower()
        or "y"
    )
    existing_client_id = None
    if app_choice != "y":
      existing_client_id = input("Enter existing Entra App Client ID: ").strip()

    # 8. CMEK Choice
    cmek_choice = (
        input("Use Customer-Managed Encryption Key (CMEK) for Secret Manager? (y/n) [default: n]: ")
        .strip()
        .lower()
        or "n"
    )
    cmek_kms_key = None
    if cmek_choice == "y":
      cmek_kms_key = input("Enter Cloud KMS Key URI (projects/.../cryptoKeys/...): ").strip()

    # 9. Gemini Engine / App ID
    engine_id = input("Enter target Gemini Enterprise Engine/App ID to bind to (optional): ").strip()

    # 10. Data Store / Collection ID
    datastore_id = (
        input("Enter Data Store ID [default: onedrive-ds]: ").strip()
        or "onedrive-ds"
    )

    return {
        "gcp_project": project_id,
        "location": location,
        "mode": mode,
        "access_level": access_level,
        "o365_env": o365_env,
        "tenant_domain": tenant_domain,
        "instance_uri": instance_uri,
        "entra_tenant_id": tenant_id,
        "existing_client_id": existing_client_id,
        "cmek_kms_key": cmek_kms_key,
        "engine_id": engine_id,
        "datastore_id": datastore_id,
        "is_global_admin": defaults.get("is_global_admin", False),
    }

  def validate_config(self, config: Dict[str, Any]) -> List[str]:
    """Validate configuration options non-destructively."""
    errors: List[str] = []
    if not config.get("gcp_project"):
      errors.append("Missing required configuration: 'gcp_project'.")
    if not config.get("entra_tenant_id"):
      errors.append("Missing required configuration: 'entra_tenant_id'.")

    instance_uri = (config.get("instance_uri") or "").strip()
    if not instance_uri:
      errors.append("OneDrive site URL ('instance_uri') cannot be empty.")
    elif not (instance_uri.startswith("http://") or instance_uri.startswith("https://")):
      errors.append("Invalid 'instance_uri'. Must start with https://")

    return errors

  def execute_dry_run(self, config: Dict[str, Any]) -> str:
    """Render a dry-run plan showing all proposed mutations."""
    mode = config.get("mode", "FEDERATED").upper()
    access_level = config.get("access_level", "READ_WRITE").upper()
    is_global_admin = config.get("is_global_admin", False)
    existing_id = config.get("existing_client_id")
    app_reg_str = f"Reuse Existing ({existing_id})" if existing_id else "Create New App"

    enabled_actions = resolve_enabled_actions("onedrive", access_level=access_level)

    plan_lines = [
        "\033[1m========================================================================\033[0m",
        "\033[1m                  ONEDRIVE CONNECTOR DRY-RUN / CHANGE PLAN              \033[0m",
        "\033[1m========================================================================\033[0m",
        f"1. Connector Mode:             {mode}",
        f"2. Action Access Tier:         {access_level} ({len(enabled_actions)} BAP actions)",
        f"3. OneDrive Site URL:          {config.get('instance_uri')}",
        f"4. GCP APIs to Enable:         discoveryengine, secretmanager, iam, cloudresourcemanager",
        f"5. Entra ID App Registration:  {app_reg_str}",
        f"6. Admin Consent Action:       {'Automatic Grant (Global Admin)' if is_global_admin else 'Manual Instructions Guidance'}",
        f"7. Secret Manager Storage:     '{config.get('datastore_id', 'onedrive-ds')}-oauth-secret'",
        f"8. Discovery Engine Data Store: '{config.get('datastore_id', 'onedrive-ds')}'",
        f"9. Engine Linkage:             {'Bind to Engine ' + config.get('engine_id') if config.get('engine_id') else 'Skipped'}",
        "\033[1m========================================================================\033[0m",
    ]
    return "\n".join(plan_lines)

  def provision(
      self, config: Dict[str, Any], dry_run: bool = False
  ) -> Dict[str, Any]:
    """Execute end-to-end provisioning of Entra ID and GCP resources."""
    project_id = config["gcp_project"]
    location = config.get("location", "global")
    datastore_id = config.get("datastore_id", "onedrive-ds")
    instance_uri = config["instance_uri"].rstrip("/")
    tenant_id = config["entra_tenant_id"]
    mode = config.get("mode", "FEDERATED").upper()
    access_level = config.get("access_level", "READ_WRITE").upper()
    o365_env = config.get("o365_env", "com")
    is_global_admin = config.get("is_global_admin", False)

    if dry_run:
      self.logger.info("%s", self.execute_dry_run(config))
      return {
          "client_id": "DRY_RUN_CLIENT_ID",
          "secret_path": f"projects/{project_id}/secrets/{datastore_id}-oauth-secret/versions/latest",
          "datastore_id": datastore_id,
          "admin_consent_granted": is_global_admin,
      }

    # 1. Enable GCP APIs
    self.gcp_provider.enable_apis(project_id)

    # 2. Entra ID App Registration & Least-Privilege Permissions
    app_name = f"Gemini-Enterprise-OneDrive-{datastore_id}"
    client_id, _ = self.entra_provider.get_or_create_app_registration(
        app_name=app_name,
        existing_client_id=config.get("existing_client_id"),
    )

    self.entra_provider.configure_permissions(
        client_id=client_id,
        connectors=["onedrive"],
        mode=mode,
        access_level=access_level,
    )
    consent_granted = self.entra_provider.handle_admin_consent(
        client_id, is_global_admin
    )

    # 3. Mint Client Secret synced with Entra policy
    client_secret, expiration_date = self.entra_provider.generate_client_secret(client_id)

    # 4. Vault Secret in Secret Manager
    secret_id = f"{datastore_id}-oauth-secret"
    secret_path = self.gcp_provider.store_secret(
        project_id=project_id,
        secret_id=secret_id,
        secret_value=client_secret,
        expiration_date=expiration_date,
        cmek_kms_key=config.get("cmek_kms_key"),
    )

    # 5. Construct BAP Payload and Provision Discovery Engine Connector
    # ValidateSourceParametersByConnectorSource allowlist for 'onedrive':
    # Top-level params: {client_id, client_secret, tenant_id, instance_uri}
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "tenant_id": tenant_id,
        "instance_uri": instance_uri,
    }

    action_params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "tenant_id": tenant_id,
        "o365_environment_type": o365_env,
        "azure_tenant": "common",
    }

    entities = [{"entityName": "file"}]
    enabled_actions = resolve_enabled_actions("onedrive", access_level=access_level)
    parsed_host = urlparse(instance_uri).netloc or instance_uri

    connector_payload = self.gcp_provider.build_bap_connector_payload(
        data_source="onedrive",
        mode=mode,
        params=params,
        action_params=action_params,
        entities=entities,
        enabled_actions=enabled_actions,
        destination_host=instance_uri,
        refresh_interval="86400s",
    )

    self.gcp_provider.create_discovery_engine_connector(
        project_id=project_id,
        location=location,
        collection_id=datastore_id,
        collection_display_name=f"Microsoft OneDrive ({parsed_host})",
        connector_payload=connector_payload,
    )

    # 6. Bind Data Store to Engine/App
    if config.get("engine_id"):
      self.gcp_provider.bind_data_store_to_engine(
          project_id=project_id,
          location=location,
          engine_id=config["engine_id"],
          datastore_id=datastore_id,
      )

    return {
        "client_id": client_id,
        "secret_path": secret_path,
        "datastore_id": datastore_id,
        "admin_consent_granted": consent_granted,
        "expiration_date": expiration_date,
    }

  def verify(
      self,
      config: Dict[str, Any],
      provision_result: Dict[str, Any],
  ) -> bool:
    """Verify post-flight health of provisioned Data Store."""
    project_id = config["gcp_project"]
    location = config.get("location", "global")
    datastore_id = provision_result.get("datastore_id") or config.get("datastore_id", "onedrive-ds")
    return self.gcp_provider.poll_health(project_id, location, datastore_id)

  def generate_terraform(
      self, config: Dict[str, Any], output_dir: str
  ) -> List[str]:
    """Generate Terraform configuration files in the specified output directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, "terraform_templates", "onedrive")
    if not os.path.exists(template_dir):
      raise FileNotFoundError(f"Template directory not found at: {template_dir}")

    target_output_dir = output_dir if os.path.isabs(output_dir) else os.path.join(base_dir, output_dir)
    os.makedirs(target_output_dir, exist_ok=True)

    gcp_project = config.get("gcp_project", "")
    gcp_location = config.get("location", "global")
    gcp_region = "us-central1" if gcp_location in ["global", "us"] else (
        "europe-west1" if gcp_location == "eu" else "us-central1"
    )
    mode = config.get("mode", "FEDERATED").upper()
    access_level = config.get("access_level", "READ_WRITE").upper()
    o365_env = config.get("o365_env", "com")
    instance_uri = config.get("instance_uri", "")
    datastore_id = config.get("datastore_id", "onedrive-ds")
    engine_id = config.get("engine_id", "")
    entra_tenant_id = config.get("entra_tenant_id", "")
    cmek_kms_key = config.get("cmek_kms_key")
    existing_client_id = config.get("existing_client_id")

    cmek_kms_key_tf = json.dumps(cmek_kms_key) if cmek_kms_key else "null"
    existing_client_id_tf = json.dumps(existing_client_id) if existing_client_id else "null"

    replacements = {
        "__GCP_PROJECT__": gcp_project,
        "__GCP_LOCATION__": gcp_location,
        "__GCP_REGION__": gcp_region,
        "__CONNECTOR_MODE__": mode,
        "__ACTION_ACCESS_LEVEL__": access_level,
        "__O365_ENV__": o365_env,
        "__ENTRA_TENANT_ID__": entra_tenant_id,
        "__INSTANCE_URI__": instance_uri,
        "__DATASTORE_ID__": datastore_id,
        "__ENGINE_ID__": engine_id,
        "__CMEK_KMS_KEY_TF__": cmek_kms_key_tf,
        "__EXISTING_CLIENT_ID_TF__": existing_client_id_tf,
    }

    generated_files = []
    for filename in sorted(os.listdir(template_dir)):
      src_path = os.path.join(template_dir, filename)
      if not os.path.isfile(src_path):
        continue

      dest_filename = filename[:-4] if filename.endswith(".tpl") else filename
      dest_path = os.path.join(target_output_dir, dest_filename)

      with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

      for placeholder, val in replacements.items():
        content = content.replace(placeholder, val)

      with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

      generated_files.append(dest_path)
      self.logger.info("Generated Terraform file: %s", dest_path)

    return generated_files

