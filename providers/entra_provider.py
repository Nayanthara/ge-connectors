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

  SHAREPOINT_APP_ID = "00000003-0000-0ff1-ce00-000000000000"
  PERMISSION_SITES_SEARCH_ALL = "3b56c6d6-ee54-4826-8880-35439402e3b2"
  PERMISSION_ALLSITES_READ = "57ab8481-7910-449e-ae0a-81a1a79f6b98"

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
      azure_cloud: str = "AzureCloud",  # pylint: disable=unused-argument
      existing_client_id: typing.Optional[str] = None,
      dry_run: bool = False,
  ) -> typing.Tuple[str, bool]:
    """Create a new Entra ID App Registration or bind to an existing one.

    Args:
        app_name: Display name for the application.
        redirect_uris: List of web callback URIs to register.
        azure_cloud: Target Azure environment (default: AzureCloud).
        existing_client_id: Optional Client ID of an existing app to re-use.
        dry_run: If True, simulates action without creating resources.

    Returns:
        Tuple of (client_id, is_newly_created).
    """
    if existing_client_id:
      self.logger.info("Using existing Client ID: %s", existing_client_id)
      return existing_client_id, False

    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would search or create Entra App Registration '%s'.",
          app_name,
      )
      return "00000000-0000-0000-0000-000000000000", True

    # Check if app already exists by name
    self.logger.info(
        "Checking for existing App Registration named '%s'...", app_name
    )
    check_cmd = (
        f'az ad app list --display-name "{app_name}" --query "[0]" -o json'
    )
    existing_res = self._run_cmd(check_cmd, check=False)

    if (
        existing_res.returncode == 0
        and existing_res.stdout.strip()
        and existing_res.stdout.strip() != "null"
    ):
      app_data = json.loads(existing_res.stdout)
      client_id = app_data["appId"]
      self.logger.info(
          "Found existing App Registration (Client ID: %s).", client_id
      )

      redirect_str = " ".join(redirect_uris)
      update_cmd = (
          f"az ad app update --id {client_id} --web-redirect-uris"
          f" {redirect_str}"
      )
      self._run_cmd(update_cmd)
      return client_id, False

    # Create new App Registration
    self.logger.info("Creating new Entra ID App Registration '%s'...", app_name)
    redirect_str = " ".join(redirect_uris)
    create_cmd = (
        f'az ad app create --display-name "{app_name}" '
        f"--web-redirect-uris {redirect_str} "
        '--sign-in-audience "AzureADMyOrg" -o json'
    )
    created_app = json.loads(self._run_cmd(create_cmd).stdout)
    client_id = created_app["appId"]
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
    """Assign delegated SharePoint API permissions.

    Args:
        client_id: Entra Application Client ID.
        dry_run: If True, simulates action without modifying state.
    """
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would assign Sites.Search.All and AllSites.Read to %s.",
          client_id,
      )
      return

    self.logger.info("Configuring delegated SharePoint API permissions...")
    perm_cmd = (
        f"az ad app permission add --id {client_id} --api"
        f" {self.SHAREPOINT_APP_ID} --api-permissions"
        f" {self.PERMISSION_SITES_SEARCH_ALL}=Scope"
        f" {self.PERMISSION_ALLSITES_READ}=Scope"
    )
    self._run_cmd(perm_cmd, check=False)
    self.logger.info("SharePoint delegated API permissions added.")

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
      consent_cmd = (
          f"az ad app permission grant --id {client_id} "
          f"--api {self.SHAREPOINT_APP_ID} --admin-consent"
      )
      res = self._run_cmd(consent_cmd, check=False)
      if res.returncode == 0:
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
    res_json = json.loads(self._run_cmd(secret_cmd).stdout)

    secret_value = res_json.get("password", "")
    expiration_date = res_json.get("endDate", "2027-01-01T00:00:00Z")

    self.logger.info(
        "Client Secret generated successfully. Expiration Date: %s",
        expiration_date,
    )
    return secret_value, expiration_date
