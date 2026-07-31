"""Microsoft Entra ID Service Provider Module.

Provides robust interaction with Microsoft Entra ID (Azure AD) via Azure CLI
(`az`).
"""

import json
import logging
import subprocess
import typing


class EntraProvider:
  """Service Provider for Microsoft Entra ID operations."""

  GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"
  SHAREPOINT_APP_ID = "00000003-0000-0ff1-ce00-000000000000"

  # Microsoft Graph API Permissions
  PERMISSION_GRAPH_USER_READ = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"

  # Office 365 SharePoint Online API Permissions
  PERMISSION_SHAREPOINT_SITES_SEARCH_ALL = (
      "1002502a-9a71-4426-8551-69ab83452fab"
  )
  PERMISSION_SHAREPOINT_SITES_READ_ALL = "4e0d77b0-96ba-4398-af14-3baa780278f4"

  def __init__(self, logger: logging.Logger, rollback_mgr: typing.Any):
    self.logger = logger
    self.rollback_mgr = rollback_mgr

  def _run_cmd(
      self, cmd: str, check: bool = True
  ) -> subprocess.CompletedProcess[str]:
    """Execute an Azure CLI command and return CompletedProcess."""
    try:
      return subprocess.run(
          cmd, shell=True, check=check, capture_output=True, text=True
      )
    except subprocess.CalledProcessError as e:
      self.logger.error("Entra ID command failed: %s", cmd)
      if e.stderr:
        self.logger.error("Stderr: %s", e.stderr.strip())
      raise e

  def get_tenant_info(self) -> typing.Dict[str, str]:
    """Fetch active Entra tenant details."""
    res = subprocess.run(
        "az account show -o json",
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0 and res.stdout.strip():
      return json.loads(res.stdout)
    return {}

  def get_or_create_app_registration(
      self,
      app_name: str,
      redirect_uris: typing.List[str],
      existing_client_id: typing.Optional[str] = None,
      dry_run: bool = False,
  ) -> typing.Tuple[str, bool]:
    """Provision a new Entra ID App Registration or reuse existing ID.

    Args:
        app_name: Display Name for Entra App.
        redirect_uris: Web redirect URIs list.
        existing_client_id: Optional existing client ID string.
        dry_run: If True, simulates action without modifying state.

    Returns:
        Tuple of (client_id, is_newly_created).
    """
    if existing_client_id:
      self.logger.info(
          "Reusing existing Entra Client ID: %s", existing_client_id
      )
      return existing_client_id, False

    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would create Entra ID App Registration '%s' with URIs %s.",
          app_name,
          redirect_uris,
      )
      return "DRY_RUN_CLIENT_ID", True

    self.logger.info("Creating Entra ID App Registration '%s'...", app_name)
    uri_str = " ".join(redirect_uris)
    create_cmd = (
        f"az ad app create --display-name '{app_name}' --web-redirect-uris"
        f" {uri_str} --sign-in-audience AzureADMyOrg -o json"
    )
    res = self._run_cmd(create_cmd)
    app_data = json.loads(res.stdout)
    client_id = app_data["appId"]

    self.logger.info(
        "App Registration created successfully. Client ID: %s", client_id
    )

    # Register rollback cleanup handler
    def cleanup_app():
      self.logger.warning(
          "Rollback: Deleting transient Entra App (%s)...", client_id
      )
      subprocess.run(
          f"az ad app delete --id {client_id}",
          shell=True,
          capture_output=True,
          check=False,
      )

    self.rollback_mgr.register(
        f"Delete Entra App Registration ({client_id})", cleanup_app
    )
    return client_id, True

  def configure_sharepoint_permissions(
      self, client_id: str, dry_run: bool = False
  ) -> None:
    """Assign delegated SharePoint and Graph permissions to App Registration.

    Args:
        client_id: Entra Application Client ID.
        dry_run: If True, simulates action without modifying state.
    """
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would assign SharePoint & Graph delegated permissions to"
          " %s.",
          client_id,
      )
      return

    self.logger.info(
        "Configuring delegated Office 365 SharePoint Online & Graph"
        " permissions..."
    )
    # Add Office 365 SharePoint Online API Permissions
    spo_perm_cmd = (
        f"az ad app permission add --id {client_id} --api"
        f" {self.SHAREPOINT_APP_ID} --api-permissions"
        f" {self.PERMISSION_SHAREPOINT_SITES_SEARCH_ALL}=Scope"
        f" {self.PERMISSION_SHAREPOINT_SITES_READ_ALL}=Scope"
    )
    self._run_cmd(spo_perm_cmd, check=False)

    # Add Microsoft Graph API Permissions (User.Read)
    graph_perm_cmd = (
        f"az ad app permission add --id {client_id} --api"
        f" {self.GRAPH_APP_ID} --api-permissions"
        f" {self.PERMISSION_GRAPH_USER_READ}=Scope"
    )
    self._run_cmd(graph_perm_cmd, check=False)
    self.logger.info(
        "Delegated SharePoint & Graph permissions added successfully."
    )

  def handle_admin_consent(
      self, client_id: str, is_global_admin: bool, dry_run: bool = False
  ) -> bool:
    """Execute automatic Admin Consent if Global Admin, or report manual instructions.

    Args:
        client_id: Entra Application Client ID.
        is_global_admin: True if user holds Global Admin role.
        dry_run: If True, simulates action without modifying state.

    Returns:
        True if admin consent was granted automatically, False otherwise.
    """
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Admin Consent Mode: %s.",
          "Automatic Grant"
          if is_global_admin
          else "Manual Instructions Guidance",
      )
      return is_global_admin

    if is_global_admin:
      self.logger.info(
          "Active user has Global Administrator rights. Executing automatic"
          " Admin Consent..."
      )
      consent_cmd = f"az ad app permission admin-consent --id {client_id}"
      res = self._run_cmd(consent_cmd, check=False)
      if res.returncode == 0:
        self.logger.info("Tenant-wide Admin Consent granted successfully.")
        return True

      # Fallback to per-API grant if admin-consent CLI alias differs
      g_res = self._run_cmd(
          f"az ad app permission grant --id {client_id} --api"
          f" {self.GRAPH_APP_ID} --admin-consent",
          check=False,
      )
      s_res = self._run_cmd(
          f"az ad app permission grant --id {client_id} --api"
          f" {self.SHAREPOINT_APP_ID} --admin-consent",
          check=False,
      )
      if g_res.returncode == 0 or s_res.returncode == 0:
        self.logger.info("Tenant-wide Admin Consent granted successfully.")
        return True

      self.logger.warning("Automatic Admin Consent grant failed.")
      return False

    self.logger.warning(
        "User is not Global Admin. Automated Admin Consent skipped."
    )
    return False

  def generate_client_secret(
      self, client_id: str, dry_run: bool = False
  ) -> typing.Tuple[str, str]:
    """Mint a Client Secret matching Entra's secret expiration policy.

    Args:
        client_id: Entra Application Client ID.
        dry_run: If True, simulates action without modifying state.

    Returns:
        Tuple of (client_secret_value, expiration_iso_date_string).
    """
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would mint Client Secret for App ID %s.", client_id
      )
      return "DRY_RUN_CLIENT_SECRET_REDACTED", "2027-01-01T00:00:00Z"

    self.logger.info("Generating Client Secret in Entra ID...")
    secret_cmd = (
        f"az ad app credential reset --id {client_id} --append --years 1 -o"
        " json"
    )
    res = self._run_cmd(secret_cmd)
    cred_data = json.loads(res.stdout)
    client_secret = cred_data["password"]
    expiration_date = cred_data.get("endDate", "2027-01-01T00:00:00Z")

    self.logger.info("Client Secret generated successfully.")
    return client_secret, expiration_date
