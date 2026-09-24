"""Custom MCP Server Data Connector Plugin for Gemini Enterprise.

Automates end-to-end setup for Custom Model Context Protocol (MCP) Server actions
running on Cloud Run or any external endpoint.
"""

import json
import os
from typing import Any, Dict, List, Optional

from core.plugin_base import BaseConnectorPlugin


class CustomMcpPlugin(BaseConnectorPlugin):
  """Connector plugin for Custom MCP Server Actions."""

  @property
  def name(self) -> str:
    return "Microsoft Custom MCP Actions"

  @property
  def connector_type(self) -> str:
    return "custom_mcp"

  def prompt_config_interactive(
      self, defaults: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Prompt admin interactively for setup choices with sensible defaults."""
    print("\n\033[1m\033[95m=== CUSTOM MCP CONNECTOR CONFIGURATION ===\033[0m")

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

    # 3. Custom MCP Server URL
    mcp_url = input(
        "Enter Custom MCP Server URL (e.g. https://service-12345.us-central1.run.app/mcp): "
    ).strip()
    while not mcp_url or not (mcp_url.startswith("http://") or mcp_url.startswith("https://")):
      mcp_url = input("Custom MCP Server URL cannot be empty and must start with https://: ").strip()
    if not mcp_url.endswith("/mcp"):
      mcp_url = f"{mcp_url.rstrip('/')}/mcp"

    # 4. Entra Tenant ID
    default_tenant = defaults.get("entra_tenant_id", "")
    tenant_prompt = (
        f"Enter Entra Tenant ID [{default_tenant}]"
        if default_tenant
        else "Enter Entra Tenant ID"
    )
    tenant_id = input(f"{tenant_prompt}: ").strip() or default_tenant
    while not tenant_id:
      tenant_id = input("Entra Tenant ID cannot be empty: ").strip()

    # 5. App Registration Choice
    app_choice = (
        input("Create a new Entra ID App Registration? (y/n) [default: y]: ")
        .strip()
        .lower()
        or "y"
    )
    existing_client_id = None
    if app_choice != "y":
      existing_client_id = input("Enter existing Entra App Client ID: ").strip()

    # 6. CMEK Choice
    cmek_choice = (
        input("Use Customer-Managed Encryption Key (CMEK) for Secret Manager? (y/n) [default: n]: ")
        .strip()
        .lower()
        or "n"
    )
    cmek_kms_key = None
    if cmek_choice == "y":
      cmek_kms_key = input("Enter Cloud KMS Key URI (projects/.../cryptoKeys/...): ").strip()

    # 7. Gemini Engine / App ID
    engine_id = input("Enter target Gemini Enterprise Engine/App ID to bind to (optional): ").strip()

    # 8. Data Store / Collection ID
    datastore_id = (
        input("Enter Data Store ID [default: ms-custom-mcp-connector]: ").strip()
        or "ms-custom-mcp-connector"
    )

    return {
        "gcp_project": project_id,
        "location": location,
        "mode": "FEDERATED",
        "access_level": "READ_WRITE",
        "mcp_url": mcp_url,
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

    mcp_url = (config.get("mcp_url") or "").strip()
    if not mcp_url:
      errors.append("Missing required configuration: 'mcp_url'.")
    elif not (mcp_url.startswith("http://") or mcp_url.startswith("https://")):
      errors.append("Invalid 'mcp_url'. Must start with https://")

    return errors

  def execute_dry_run(self, config: Dict[str, Any]) -> str:
    """Render a dry-run plan showing all proposed mutations."""
    is_global_admin = config.get("is_global_admin", False)
    existing_id = config.get("existing_client_id")
    app_reg_str = f"Reuse Existing ({existing_id})" if existing_id else "Create New App"

    plan_lines = [
        "\033[1m========================================================================\033[0m",
        "\033[1m                  CUSTOM MCP CONNECTOR DRY-RUN / CHANGE PLAN            \033[0m",
        "\033[1m========================================================================\033[0m",
        "1. Connector Mode:             ACTIONS, FEDERATED",
        f"2. MCP Server URL:             {config.get('mcp_url')}",
        "3. GCP APIs to Enable:         discoveryengine, secretmanager, iam, cloudresourcemanager",
        f"4. Entra ID App Registration:  {app_reg_str}",
        f"5. Admin Consent Action:       {'Automatic Grant (Global Admin)' if is_global_admin else 'Manual Instructions Guidance'}",
        f"6. Secret Manager Storage:     '{config.get('datastore_id', 'ms-custom-mcp-connector')}-oauth-secret'",
        f"7. Discovery Engine Data Store: '{config.get('datastore_id', 'ms-custom-mcp-connector')}'",
        f"8. Engine Linkage:             {'Bind to Engine ' + config.get('engine_id') if config.get('engine_id') else 'Skipped'}",
        "\033[1m========================================================================\033[0m",
    ]
    return "\n".join(plan_lines)

  def provision(
      self, config: Dict[str, Any], dry_run: bool = False
  ) -> Dict[str, Any]:
    """Execute end-to-end provisioning of Entra ID and GCP resources."""
    project_id = config["gcp_project"]
    location = config.get("location", "global")
    datastore_id = config.get("datastore_id", "ms-custom-mcp-connector")
    tenant_id = config["entra_tenant_id"]
    mcp_url = config["mcp_url"]
    if not mcp_url.endswith("/mcp"):
      mcp_url = f"{mcp_url.rstrip('/')}/mcp"
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

    # 2. Entra ID App Registration & Permissions
    app_name = f"Gemini-Enterprise-CustomMCP-{datastore_id}"
    client_id, _ = self.entra_provider.get_or_create_app_registration(
        app_name=app_name,
        existing_client_id=config.get("existing_client_id"),
    )

    self.entra_provider.configure_permissions(
        client_id=client_id,
        connectors=["custom_mcp"],
        mode="FEDERATED",
        access_level="READ_WRITE",
    )
    consent_granted = self.entra_provider.handle_admin_consent(
        client_id, is_global_admin
    )

    # 3. Mint Client Secret
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

    # 5. Construct Custom MCP Payload
    auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    connector_payload = {
        "dataSource": "custom_mcp",
        "connectorModes": ["ACTIONS", "FEDERATED"],
        "params": {
            "oauth_access_token": "placeholder",
        },
        "actionConfig": {
            "actionParams": {
                "instance_uri": mcp_url,
                "auth_uri": auth_url,
                "token_uri": token_url,
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": "offline_access .default",
            },
            "createBapConnection": True,
            "isActionConfigured": True,
        },
        "refreshInterval": "7200s",
    }

    self.gcp_provider.create_discovery_engine_connector(
        project_id=project_id,
        location=location,
        collection_id=datastore_id,
        collection_display_name="Microsoft Custom MCP Actions",
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
    datastore_id = provision_result.get("datastore_id") or config.get("datastore_id", "ms-custom-mcp-connector")
    return self.gcp_provider.poll_health(project_id, location, datastore_id)

  def generate_terraform(
      self, config: Dict[str, Any], output_dir: str
  ) -> List[str]:
    """Generate Terraform configuration files in the specified output directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, "terraform_templates", "custom_mcp")
    if not os.path.exists(template_dir):
      raise FileNotFoundError(f"Template directory not found at: {template_dir}")

    target_output_dir = output_dir if os.path.isabs(output_dir) else os.path.join(base_dir, output_dir)
    os.makedirs(target_output_dir, exist_ok=True)

    gcp_project = config.get("gcp_project", "")
    gcp_location = config.get("location", "global")
    gcp_region = "us-central1" if gcp_location in ["global", "us"] else (
        "europe-west1" if gcp_location == "eu" else "us-central1"
    )
    mcp_url = config.get("mcp_url", "")
    datastore_id = config.get("datastore_id", "ms-custom-mcp-connector")
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
        "__MCP_URL__": mcp_url,
        "__ENTRA_TENANT_ID__": entra_tenant_id,
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

