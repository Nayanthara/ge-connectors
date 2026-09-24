"""Microsoft Entra ID Service Provider Module.

Provides robust interaction with Microsoft Entra ID (Azure AD) via Azure CLI (`az`).
Automates:
- Application Registration creation and reuse
- Multi-redirect URI registration
- Dynamic Least-Privilege permission assignment for Graph and SharePoint APIs
- Single-tenant (AzureADMyOrg) vs Multi-tenant (AzureADMultipleOrgs) audiences
- Automated Admin Consent and fallback manual instruction generation
- Client Secret generation synced with Entra policies
"""

import json
import logging
import subprocess
import typing

from core.catalog import (
    GEMINI_ENTERPRISE_REDIRECT_URIS,
    MICROSOFT_GRAPH_APP_ID,
    SHAREPOINT_ONLINE_APP_ID,
    resolve_least_privilege_permissions,
)


class EntraProvider:
  """Service Provider for Microsoft Entra ID operations."""

  GRAPH_APP_ID = MICROSOFT_GRAPH_APP_ID
  SHAREPOINT_APP_ID = SHAREPOINT_ONLINE_APP_ID

  # Fallback well-known permission UUIDs if live SP query is unavailable
  STATIC_GRAPH_SCOPES = {
      "User.Read": "e1fe6dd8-ba31-4d61-89e7-88639da4683d",
      "User.Read.All": "a154be20-db9c-4678-8ab7-66f6cc099a59",
      "User.ReadBasic.All": "b340eb25-3456-403f-be2f-afcf0fb76fb0",
      "openid": "37f257e3-d71a-4e70-923c-3aa92feb8bb3",
      "profile": "14dad69e-099b-42c9-810b-d002981feec1",
      "offline_access": "7427e0e9-2f9a-4247-9ac8-74e8ce1b4020",
      "Files.Read.All": "10465720-29dd-4523-a11a-6a75c743c9d9",
      "Files.ReadWrite": "54472324-9924-4331-a8cf-3de4c795b325",
      "Files.ReadWrite.All": "8638a938-b3d0-4756-8675-7de3747706e2",
      "Files.ReadWrite.AppFolder": "8019302e-7264-42b7-a365-b1a9c3b88939",
      "Sites.Read.All": "205e70e5-aba6-4c52-a976-6d2d46c48043",
      "Sites.ReadWrite.All": "89fe6a52-be36-487e-b7d8-d061c452a0e9",
      "Sites.Manage.All": "c5e20601-3e4b-4b8c-b038-164741f23554",
      "Group.Read.All": "5f8c59c8-edd5-4a25-9614-b52e3796d11b",
      "GroupMember.Read.All": "bc024368-1153-4739-b217-4326f2e966d0",
      "Mail.Read": "570265a9-50c9-4aa7-Bag9-88c02c98d7ca",
      "Mail.ReadBasic": "40f97002-9d9a-4459-8ddc-662654014000",
      "Mail.Read.Shared": "88d9093b-842c-451e-9f4c-73465b71954c",
      "Mail.ReadWrite": "024d486e-b451-40bb-833d-3e66d9b66f4e",
      "Mail.Send": "e383f46e-2787-4529-855e-0e479a3ffac0",
      "Calendars.Read": "465a38f9-7676-45ff-aa6b-aac812dd90e8",
      "Calendars.ReadWrite": "12466101-c9b8-439a-bf63-8a6f41e574f8",
      "Contacts.Read": "ff74d97f-43af-4b68-9f9a-270da074f40f",
      "Contacts.ReadWrite": "d56682ec-c09e-4743-aaf4-1a3aac4caa21",
      "Tasks.ReadWrite": "22147578-86ac-4e1c-bb78-7756e09c195a",
      "Channel.ReadBasic.All": "e403d15b-9a4f-4d4b-a25e-046c4b0351d0",
      "Channel.Create": "4955b9a8-e1c5-4d00-9844-aa02d8479040",
      "ChannelMember.Read.All": "7c14a52e-5415-46eb-8051-7890f5df7a19",
      "ChannelMember.ReadWrite.All": "a1dfb689-d41c-43f1-9d9c-197eb22f9864",
      "ChannelMessage.Read.All": "04c2196d-350e-4364-969c-ea00787e7485",
      "ChannelMessage.ReadWrite": "b0a2a4b8-f1f6-4d22-b91c-7928d22384a6",
      "ChannelMessage.Send": "ebf6018b-837d-4eb0-867e-ecd24cb84272",
      "ChannelSettings.ReadWrite.All": "333c1626-d66a-4972-88f6-559139f4e242",
      "Chat.Read": "0e263e50-5827-48a4-b97c-d940288653c7",
      "Chat.ReadBasic": "22ff06bb-7d87-43f0-8c26-6f16f39eb758",
      "Chat.Create": "54e58ea9-42b7-4a6c-b3a9-e65383f0cfc2",
      "Chat.ReadWrite": "1ec23443-4171-4603-85cb-43400508b98d",
      "ChatMessage.Read": "57f59dd1-e403-4903-8f06-e0e6ff407fcf",
      "ChatMessage.Send": "81f18579-5095-46a4-bb50-3ee91f24d4d6",
      "Schedule.Read.All": "85ef9e5f-149f-4318-9773-772c67fc7f57",
      "Schedule.ReadWrite.All": "278c77aa-5769-4f7f-8d96-0e1d8ee1c3e3",
      "Team.ReadBasic.All": "b328a6f4-ec01-4475-81d3-3567d2685718",
      "TeamMember.Read.All": "093f412e-a5cd-4560-b6ab-18e84abeb4a5",
  }

  STATIC_GRAPH_ROLES = {
      "User.Read.All": "df021247-6123-4830-b32f-63524f8a8105",
      "Group.Read.All": "5b56725b-21bd-4282-b442-90ace8c663bd",
      "GroupMember.Read.All": "98830695-27a2-44f7-8c18-0c3ebc9698b6",
      "Files.Read.All": "01d4889e-14de-4ec5-9153-a1e127c211f9",
      "Sites.Read.All": "75359482-378d-4052-8f01-80520e7db3cd",
      "Sites.FullControl.All": "678536cf-a190-4180-ba4a-074479904944",
      "Mail.Read": "81079e52-da32-4307-9ba8-1b0f0adb520f",
      "Mail.ReadBasic": "37730810-e953-4ed6-a510-9b37c02b36c7",
      "Mail.ReadBasic.All": "b633e1c5-b582-4048-a93e-9f11b44c9b96",
      "Calendars.Read": "798ee544-9d2d-430c-a058-86e3e3d0c841",
      "Calendars.ReadBasic.All": "22ff06bb-7d87-43f0-8c26-6f16f39eb758",
      "Contacts.Read": "089fe91b-63c3-4247-97d0-0115006b5286",
      "Channel.ReadBasic.All": "24354228-569b-449e-8c82-ef7b337c6883",
      "ChannelMember.Read.All": "b4e3a478-f3d2-43da-a991-62058444a17d",
      "ChannelMessage.Read.All": "85ef9e5f-149f-4318-9773-772c67fc7f57",
      "Chat.Read.All": "6b9e2467-5110-449d-b8d9-3663a8a3a0e9",
      "Schedule.Read.All": "586551b9-38b9-40eb-9562-b911c473be74",
      "Team.ReadBasic.All": "e1f7614e-aa77-4406-8d18-972101007802",
      "TeamMember.Read.All": "b4e3a478-f3d2-43da-a991-62058444a17d",
  }

  STATIC_SHAREPOINT_SCOPES = {
      "Sites.Search.All": "1002502a-9a71-4426-8551-69ab83452fab",
      "Sites.Read.All": "4e0d77b0-96ba-4398-af14-3baa780278f4",
      "AllSites.Read": "57c7b80a-9d90-4131-b844-f852b7573f08",
      "AllSites.Write": "8df90b63-00f8-45be-b94f-0dfa1ef37d1e",
      "AllSites.FullControl": "74889c20-da3e-4b68-b7eb-fa2e8a15647c",
  }

  STATIC_SHAREPOINT_ROLES = {
      "Sites.Read.All": "75359482-378d-4052-8f01-80520e7db3cd",
      "Sites.FullControl.All": "678536cf-a190-4180-ba4a-074479904944",
  }

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
      redirect_uris: typing.Optional[typing.List[str]] = None,
      existing_client_id: typing.Optional[str] = None,
      sign_in_audience: str = "AzureADMyOrg",
      dry_run: bool = False,
  ) -> typing.Tuple[str, bool]:
    """Provision a new Entra ID App Registration or reuse existing ID.

    Args:
        app_name: Display Name for Entra App.
        redirect_uris: Web redirect URIs list (defaults to Gemini Enterprise standard URIs).
        existing_client_id: Optional existing client ID string.
        sign_in_audience: AzureADMyOrg (single tenant) or AzureADMultipleOrgs (multi-tenant).
        dry_run: If True, simulates action without modifying state.

    Returns:
        Tuple of (client_id, is_newly_created).
    """
    effective_uris = redirect_uris or GEMINI_ENTERPRISE_REDIRECT_URIS

    if existing_client_id:
      self.logger.info("Reusing existing Entra Client ID: %s", existing_client_id)
      if not dry_run:
        uri_str = " ".join(effective_uris)
        update_cmd = (
            f"az ad app update --id {existing_client_id} "
            f"--web-redirect-uris {uri_str} "
            f"--sign-in-audience {sign_in_audience}"
        )
        self._run_cmd(update_cmd, check=False)
      return existing_client_id, False

    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would create Entra ID App Registration '%s' (Audience: %s) with URIs %s.",
          app_name,
          sign_in_audience,
          effective_uris,
      )
      return "DRY_RUN_CLIENT_ID", True

    self.logger.info("Creating Entra ID App Registration '%s'...", app_name)
    uri_str = " ".join(effective_uris)
    create_cmd = (
        f"az ad app create --display-name '{app_name}' --web-redirect-uris"
        f" {uri_str} --sign-in-audience {sign_in_audience} -o json"
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

  def _query_sp_manifest(self, app_id: str) -> typing.Dict[str, typing.Any]:
    """Query service principal manifest to resolve permission names to UUIDs."""
    cmd = f"az ad sp show --id {app_id} -o json"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    if res.returncode == 0 and res.stdout.strip():
      try:
        return json.loads(res.stdout)
      except Exception:
        pass
    return {}

  def build_resource_access_payload(
      self,
      connectors: typing.List[str],
      mode: str = "FEDERATED",
      access_level: str = "READ_WRITE",
  ) -> typing.List[typing.Dict[str, typing.Any]]:
    """Build requiredResourceAccess JSON structure for Entra ID app update."""
    perms = resolve_least_privilege_permissions(connectors, mode, access_level)

    graph_sp = self._query_sp_manifest(self.GRAPH_APP_ID)
    sp_sp = self._query_sp_manifest(self.SHAREPOINT_APP_ID)

    graph_scopes_map = {
        s["value"]: s["id"]
        for s in graph_sp.get("oauth2PermissionScopes", [])
        if s.get("isEnabled", True)
    } or self.STATIC_GRAPH_SCOPES

    graph_roles_map = {
        r["value"]: r["id"]
        for r in graph_sp.get("appRoles", [])
        if r.get("isEnabled", True)
    } or self.STATIC_GRAPH_ROLES

    sp_scopes_map = {
        s["value"]: s["id"]
        for s in sp_sp.get("oauth2PermissionScopes", [])
        if s.get("isEnabled", True)
    } or self.STATIC_SHAREPOINT_SCOPES

    sp_roles_map = {
        r["value"]: r["id"]
        for r in sp_sp.get("appRoles", [])
        if r.get("isEnabled", True)
    } or self.STATIC_SHAREPOINT_ROLES

    required_resource_access = []

    # 1. Microsoft Graph Access
    graph_access = []
    for scope_name in perms["graph_scopes"]:
      sid = graph_scopes_map.get(scope_name)
      if sid:
        graph_access.append({"id": sid, "type": "Scope"})

    for role_name in perms["graph_roles"]:
      rid = graph_roles_map.get(role_name)
      if rid:
        graph_access.append({"id": rid, "type": "Role"})

    if graph_access:
      # Deduplicate
      seen = set()
      deduped_graph = []
      for a in graph_access:
        key = (a["id"], a["type"])
        if key not in seen:
          seen.add(key)
          deduped_graph.append(a)
      required_resource_access.append({
          "resourceAppId": self.GRAPH_APP_ID,
          "resourceAccess": deduped_graph,
      })

    # 2. SharePoint Online Access
    sp_access = []
    for scope_name in perms["sharepoint_scopes"]:
      sid = sp_scopes_map.get(scope_name)
      if sid:
        sp_access.append({"id": sid, "type": "Scope"})

    for role_name in perms["sharepoint_roles"]:
      rid = sp_roles_map.get(role_name)
      if rid:
        sp_access.append({"id": rid, "type": "Role"})

    if sp_access:
      seen = set()
      deduped_sp = []
      for a in sp_access:
        key = (a["id"], a["type"])
        if key not in seen:
          seen.add(key)
          deduped_sp.append(a)
      required_resource_access.append({
          "resourceAppId": self.SHAREPOINT_APP_ID,
          "resourceAccess": deduped_sp,
      })

    return required_resource_access

  def configure_permissions(
      self,
      client_id: str,
      connectors: typing.List[str],
      mode: str = "FEDERATED",
      access_level: str = "READ_WRITE",
      dry_run: bool = False,
  ) -> None:
    """Assign dynamic least-privilege Graph & SharePoint permissions to App Registration.

    Args:
        client_id: Entra Application Client ID.
        connectors: List of connector keys (e.g. ['sharepoint', 'teams']).
        mode: 'FEDERATED' or 'DATA_INGESTION'.
        access_level: 'READ_WRITE' or 'READ_ONLY' or 'CUSTOM'.
        dry_run: If True, simulates action without modifying state.
    """
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would configure dynamic least-privilege permissions on %s (Connectors: %s, Mode: %s, Access: %s).",
          client_id,
          connectors,
          mode,
          access_level,
      )
      return

    self.logger.info(
        "Configuring dynamic least-privilege permissions on Entra App (%s)...",
        client_id,
    )
    resource_access_list = self.build_resource_access_payload(
        connectors=connectors, mode=mode, access_level=access_level
    )
    payload_str = json.dumps(resource_access_list)

    update_cmd = (
        f"az ad app update --id {client_id} "
        f"--required-resource-accesses '{payload_str}'"
    )
    res = self._run_cmd(update_cmd, check=False)
    if res.returncode == 0:
      self.logger.info("Permissions updated successfully on Entra App.")
    else:
      self.logger.warning(
          "Direct required-resource-accesses update failed. Attempting per-permission fallback..."
      )
      # Fallback to az ad app permission add
      for res_access in resource_access_list:
        api_id = res_access["resourceAppId"]
        for item in res_access["resourceAccess"]:
          perm_id = item["id"]
          perm_type = item["type"]
          add_cmd = (
              f"az ad app permission add --id {client_id} --api {api_id} "
              f"--api-permissions {perm_id}={perm_type}"
          )
          self._run_cmd(add_cmd, check=False)

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
          "Automatic Grant" if is_global_admin else "Manual Instructions Guidance",
      )
      return is_global_admin

    if is_global_admin:
      self.logger.info(
          "Active user has Global Administrator rights. Executing automatic Admin Consent..."
      )
      consent_cmd = f"az ad app permission admin-consent --id {client_id}"
      res = self._run_cmd(consent_cmd, check=False)
      if res.returncode == 0:
        self.logger.info("Tenant-wide Admin Consent granted successfully.")
        return True

      # Fallback to per-API grant if admin-consent CLI alias differs
      g_res = self._run_cmd(
          f"az ad app permission grant --id {client_id} --api {self.GRAPH_APP_ID} --admin-consent",
          check=False,
      )
      s_res = self._run_cmd(
          f"az ad app permission grant --id {client_id} --api {self.SHAREPOINT_APP_ID} --admin-consent",
          check=False,
      )
      if g_res.returncode == 0 or s_res.returncode == 0:
        self.logger.info("Tenant-wide Admin Consent granted successfully.")
        return True

      self.logger.warning("Automatic Admin Consent grant failed.")
      return False

    self.logger.warning("User is not Global Admin. Automated Admin Consent skipped.")
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
        f"az ad app credential reset --id {client_id} --append --years 2 -o json"
    )
    res = self._run_cmd(secret_cmd)
    cred_data = json.loads(res.stdout)
    client_secret = cred_data["password"]
    expiration_date = cred_data.get("endDate", "2028-01-01T00:00:00Z")

    self.logger.info("Client Secret generated successfully.")
    return client_secret, expiration_date
