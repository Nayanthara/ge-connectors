"""SharePoint Federated Search Connector Plugin for Gemini Enterprise.

Implements the BaseConnectorPlugin interface to automate end-to-end setup for:
- Microsoft SharePoint Online Federated Search
"""

import typing

from core.plugin_base import BaseConnectorPlugin


class SharePointFederatedPlugin(BaseConnectorPlugin):
  """Connector plugin for Microsoft SharePoint Online Federated Search."""

  REDIRECT_URIS = [
      "https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html",
      "https://vertexaisearch.cloud.google.com/oauth-redirect",
  ]

  @property
  def name(self) -> str:
    return "Microsoft SharePoint Online (Federated Search)"

  @property
  def connector_type(self) -> str:
    return "sharepoint_federated"

  def prompt_config_interactive(
      self, defaults: typing.Dict[str, typing.Any]
  ) -> typing.Dict[str, typing.Any]:
    """Prompt admin interactively for setup choices with sensible defaults."""
    print(
        "\n\033[1m\033[95m=== SHAREPOINT FEDERATED CONNECTOR CONFIGURATION"
        " ===\033[0m"
    )

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
    location = (
        input("Enter GCP Location [default: global]: ").strip() or "global"
    )

    # 3. SharePoint Instance URL
    instance_uri = input(
        "Enter SharePoint Instance URL (e.g. https://acme.sharepoint.com): "
    ).strip()
    while not instance_uri.startswith(
        "http://"
    ) and not instance_uri.startswith("https://"):
      instance_uri = input(
          "Please enter a valid URL starting with https:// : "
      ).strip()
    instance_uri = instance_uri.rstrip("/")

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

    # 5. App Registration Choice (New vs Existing)
    app_choice = (
        input("Create a new Entra ID App Registration? (y/n) [default: y]: ")
        .strip()
        .lower()
        or "y"
    )
    existing_client_id = None
    if app_choice != "y":
      existing_client_id = input("Enter existing Entra App Client ID: ").strip()

    # 6. Encryption Key Choice (Google-managed vs CMEK)
    cmek_choice = (
        input(
            "Use Customer-Managed Encryption Key (CMEK) for Secret Manager?"
            " (y/n) [default: n]: "
        )
        .strip()
        .lower()
        or "n"
    )
    cmek_kms_key = None
    if cmek_choice == "y":
      cmek_kms_key = input(
          "Enter Cloud KMS Key URI (projects/.../cryptoKeys/...): "
      ).strip()

    # 7. Gemini Engine / App ID (Optional)
    engine_id = input(
        "Enter target Gemini Enterprise Engine/App ID to bind to (optional): "
    ).strip()

    # 8. Data Store ID
    datastore_id = (
        input(
            "Enter Data Store ID [default: sharepoint-federated-ds]: "
        ).strip()
        or "sharepoint-federated-ds"
    )

    return {
        "gcp_project": project_id,
        "location": location,
        "instance_uri": instance_uri,
        "entra_tenant_id": tenant_id,
        "existing_client_id": existing_client_id,
        "cmek_kms_key": cmek_kms_key,
        "engine_id": engine_id,
        "datastore_id": datastore_id,
        "is_global_admin": defaults.get("is_global_admin", False),
    }

  def validate_config(
      self, config: typing.Dict[str, typing.Any]
  ) -> typing.List[str]:
    """Validate configuration options non-destructively."""
    errors: typing.List[str] = []
    if not config.get("gcp_project"):
      errors.append("Missing required configuration: 'gcp_project'.")
    if not config.get("entra_tenant_id"):
      errors.append("Missing required configuration: 'entra_tenant_id'.")

    instance_uri = config.get("instance_uri", "")
    if not instance_uri or not (
        instance_uri.startswith("http://")
        or instance_uri.startswith("https://")
    ):
      errors.append(
          "Invalid or missing 'instance_uri'. Must start with https://"
      )

    return errors

  def execute_dry_run(self, config: typing.Dict[str, typing.Any]) -> str:
    """Render a dry-run plan showing all proposed mutations."""
    is_global_admin = config.get("is_global_admin", False)
    existing_id = config.get("existing_client_id")
    app_reg_str = (
        "Create New App"
        if not existing_id
        else f"Reuse Existing ({existing_id})"
    )
    gcp_proj = config.get("gcp_project")
    gcp_loc = config.get("location")
    ds_id = config.get("datastore_id")

    plan_lines = [
        "\033[1m========================================================================\033[0m",
        (
            "\033[1m                        DRY-RUN / CHANGE PLAN              "
            "             \033[0m"
        ),
        "\033[1m========================================================================\033[0m",
        (
            "1. GCP APIs to Enable:         discoveryengine, secretmanager,"
            " iam, cloudresourcemanager"
        ),
        f"2. Entra ID App Registration:  {app_reg_str}",
        f"3. Redirect URIs:              {', '.join(self.REDIRECT_URIS)}",
        (
            "4. Delegated Permissions:      SharePoint API (Sites.Search.All,"
            " AllSites.Read)"
        ),
        (
            "5. Admin Consent Action:      "
            f" {'Automatic Grant (Global Admin Detected)' if is_global_admin else 'Manual Instructions Guidance (Cloud App Admin)'}"
        ),
        (
            "6. Secret Manager Storage:     Container"
            " 'sharepoint-federated-oauth-secret'"
        ),
        (
            "7. Encryption Key Mode:       "
            f" {config.get('cmek_kms_key') or 'Google-Managed Keys'}"
        ),
        (
            "8. Discovery Engine DataStore: Create"
            f" 'projects/{gcp_proj}/locations/{gcp_loc}/collections/default_collection/dataStores/{ds_id}'"
        ),
        (
            "9. Engine Linkage:            "
            f" {'Bind to Engine ' + config.get('engine_id') if config.get('engine_id') else 'Skipped (No Engine ID provided)'}"
        ),
        "\033[1m========================================================================\033[0m",
    ]
    return "\n".join(plan_lines)

  def provision(
      self, config: typing.Dict[str, typing.Any], dry_run: bool = False
  ) -> typing.Dict[str, typing.Any]:
    """Execute end-to-end provisioning of Entra ID and GCP resources."""
    project_id = config["gcp_project"]
    location = config.get("location", "global")
    datastore_id = config["datastore_id"]
    instance_uri = config["instance_uri"]
    tenant_id = config["entra_tenant_id"]
    is_global_admin = config.get("is_global_admin", False)

    if dry_run:
      self.logger.info("%s", self.execute_dry_run(config))
      return {
          "client_id": "DRY_RUN_CLIENT_ID",
          "secret_path": (
              f"projects/{project_id}/secrets/sharepoint-federated-oauth-secret/versions/latest"
          ),
          "datastore_id": datastore_id,
          "admin_consent_granted": is_global_admin,
      }

    # 1. Enable GCP APIs
    self.gcp_provider.enable_apis(project_id)

    # 2. Entra ID App Registration & Permissions
    app_name = "Gemini-Enterprise-SharePoint-Federated"
    client_id, _is_new = (  # pylint: disable=unused-variable
        self.entra_provider.get_or_create_app_registration(
            app_name=app_name,
            redirect_uris=self.REDIRECT_URIS,
            existing_client_id=config.get("existing_client_id"),
        )
    )

    self.entra_provider.configure_sharepoint_permissions(client_id)
    consent_granted = self.entra_provider.handle_admin_consent(
        client_id, is_global_admin
    )

    # 3. Mint Client Secret synced with Entra policy
    client_secret, expiration_date = self.entra_provider.generate_client_secret(
        client_id
    )

    # 4. Vault Secret in Secret Manager
    secret_id = "sharepoint-federated-oauth-secret"
    secret_path = self.gcp_provider.store_secret(
        project_id=project_id,
        secret_id=secret_id,
        secret_value=client_secret,
        expiration_date=expiration_date,
        cmek_kms_key=config.get("cmek_kms_key"),
    )

    # 5. Create Discovery Engine Data Store
    _ds_res = (  # pylint: disable=unused-variable
        self.gcp_provider.create_discovery_engine_data_store(
            project_id=project_id,
            location=location,
            datastore_id=datastore_id,
            client_id=client_id,
            tenant_id=tenant_id,
            instance_uri=instance_uri,
        )
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
      config: typing.Dict[str, typing.Any],
      provision_result: typing.Dict[str, typing.Any],
  ) -> bool:
    """Verify post-flight health of provisioned Data Store."""
    project_id = config["gcp_project"]
    location = config.get("location", "global")
    datastore_id = (
        provision_result.get("datastore_id") or config["datastore_id"]
    )

    is_active = self.gcp_provider.poll_health(
        project_id, location, datastore_id
    )
    return is_active
