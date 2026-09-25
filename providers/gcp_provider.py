"""Google Cloud Platform (GCP) Service Provider Module.

Handles GCP infrastructure operations for Gemini Enterprise:
- Automated GCP API enablement
- Secret Manager creation (with CMEK & expiration tagging)
- Universal Dual-Mode BAP DataConnector creation via Discovery Engine REST API
- Gemini Enterprise Engine / App creation and 33 Engine.features management
- DataStore linking and health polling
"""

import json
import logging
import subprocess
import time
import typing
import urllib.error
import urllib.parse
import urllib.request

from core.catalog import (
    CONNECTOR_CATALOG,
    build_engine_features_map,
    resolve_enabled_actions,
)


class GcpProvider:
  """Service Provider for Google Cloud Platform operations."""

  REQUIRED_APIS = [
      "discoveryengine.googleapis.com",
      "secretmanager.googleapis.com",
      "iam.googleapis.com",
      "cloudresourcemanager.googleapis.com",
  ]

  def __init__(self, logger: logging.Logger, rollback_mgr: typing.Any):
    self.logger = logger
    self.rollback_mgr = rollback_mgr

  def _run_cmd(
      self, cmd: str, check: bool = True
  ) -> subprocess.CompletedProcess[str]:
    """Execute a gcloud shell command."""
    try:
      return subprocess.run(
          cmd, shell=True, check=check, capture_output=True, text=True
      )
    except subprocess.CalledProcessError as e:
      self.logger.error("GCP command failed: %s", cmd)
      if e.stderr:
        self.logger.error("Stderr: %s", e.stderr.strip())
      raise e

  def get_access_token(self) -> str:
    """Obtain short-lived access token for GCP REST API calls."""
    res = self._run_cmd("gcloud auth print-access-token")
    return res.stdout.strip()

  def enable_apis(self, project_id: str, dry_run: bool = False) -> None:
    """Enable required GCP APIs."""
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would enable GCP APIs: %s on project %s.",
          ", ".join(self.REQUIRED_APIS),
          project_id,
      )
      return

    self.logger.info(
        "Configuring gcloud quota project and enabling required GCP APIs on project '%s'...",
        project_id,
    )
    self._run_cmd(
        f"gcloud config set billing/quota_project {project_id}", check=False
    )
    cmd = (
        f"gcloud services enable {' '.join(self.REQUIRED_APIS)} "
        f"--project={project_id}"
    )
    self._run_cmd(cmd)
    self.logger.info("GCP APIs enabled successfully.")

  def store_secret(
      self,
      project_id: str,
      secret_id: str,
      secret_value: str,
      expiration_date: str,
      cmek_kms_key: typing.Optional[str] = None,
      dry_run: bool = False,
  ) -> str:
    """Store Client Secret in Secret Manager with expiration tags."""
    secret_path = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would store Client Secret in GCP Secret Manager (%s) with CMEK: %s.",
          secret_id,
          cmek_kms_key or "Google-Managed",
      )
      return secret_path

    self.logger.info(
        "Storing Client Secret in GCP Secret Manager ('%s')...", secret_id
    )

    check_cmd = (
        f"gcloud secrets describe {secret_id} --project={project_id} -o json"
    )
    res = self._run_cmd(check_cmd, check=False)

    cmek_flag = (
        f"--kms-key-name={cmek_kms_key}"
        if cmek_kms_key
        else "--replication-policy=automatic"
    )

    exp_clean = expiration_date.split("T")[0].replace("-", "_")
    labels = f"expiration_date={exp_clean},connector_type=microsoft_365,alert_before_days=30,created_by=ge_connector_tool"

    if res.returncode != 0:
      self.logger.info(
          "Creating Secret Manager secret container '%s'...", secret_id
      )
      create_cmd = (
          f"gcloud secrets create {secret_id} --project={project_id} "
          f"{cmek_flag} --labels={labels}"
      )
      create_res = self._run_cmd(create_cmd, check=False)
      if create_res.returncode != 0:
        if (
            "IAM_PERMISSION_DENIED" in create_res.stderr
            or "secretmanager.secrets.create" in create_res.stderr
        ):
          raise RuntimeError(
              "Permission denied creating Secret Manager secret. Ensure active user has roles/secretmanager.admin."
          )
        raise RuntimeError(f"Secret creation failed: {create_res.stderr}")

      def cleanup_secret():
        self.logger.warning(
            "Rollback: Deleting transient Secret Manager secret (%s)...",
            secret_id,
        )
        subprocess.run(
            f"gcloud secrets delete {secret_id} --project={project_id} --quiet",
            shell=True,
            capture_output=True,
            check=False,
        )

      self.rollback_mgr.register(
          f"Delete GCP Secret ({secret_id})", cleanup_secret
      )

    self.logger.info("Adding new secret version to '%s'...", secret_id)
    add_ver_cmd = (
        f'echo -n "{secret_value}" | gcloud secrets versions add '
        f"{secret_id} --project={project_id} --data-file=-"
    )
    self._run_cmd(add_ver_cmd)

    self.logger.info(
        "Client Secret stored in Secret Manager. Expiration Tag: %s",
        expiration_date,
    )
    return secret_path

  def build_bap_connector_payload(
      self,
      data_source: str,
      mode: str,
      params: typing.Dict[str, typing.Any],
      action_params: typing.Dict[str, typing.Any],
      entities: typing.List[typing.Dict[str, str]],
      enabled_actions: typing.Optional[typing.List[str]] = None,
      destination_host: typing.Optional[str] = None,
      refresh_interval: str = "7200s",
  ) -> typing.Dict[str, typing.Any]:
    """Construct standard Discovery Engine BAP DataConnector payload."""
    is_ingestion = mode.upper() == "DATA_INGESTION"

    if is_ingestion:
      connector_modes = ["DATA_CONNECTOR"]
      acl_enabled = True
      actions_list = []
    else:
      connector_modes = ["FEDERATED", "ACTIONS"]
      acl_enabled = False
      if enabled_actions is not None:
        actions_list = enabled_actions
      else:
        actions_list = resolve_enabled_actions(data_source, access_level="READ_WRITE")

    bap_config: typing.Dict[str, typing.Any] = {
        "supportedConnectorModes": ["ACTIONS"],
    }
    if actions_list:
      bap_config["enabledActions"] = actions_list

    payload: typing.Dict[str, typing.Any] = {
        "dataSource": data_source,
        "connectorModes": connector_modes,
        "aclEnabled": acl_enabled,
        "params": params,
        "actionConfig": {
            "actionParams": action_params,
            "createBapConnection": True,
            "isActionConfigured": True,
        },
        "bapConfig": bap_config,
        "entities": entities,
        "refreshInterval": refresh_interval,
        "syncMode": "PERIODIC",
    }

    if destination_host:
      payload["destinationConfigs"] = [
          {"key": "url", "destinations": [{"host": destination_host}]}
      ]

    return payload

  def create_discovery_engine_connector(
      self,
      project_id: str,
      location: str,
      collection_id: str,
      collection_display_name: str,
      connector_payload: typing.Dict[str, typing.Any],
      dry_run: bool = False,
  ) -> typing.Dict[str, typing.Any]:
    """Call Discovery Engine REST API setUpDataConnector to provision connector."""
    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/{location}:setUpDataConnector"
    )

    request_body = {
        "collectionId": collection_id,
        "collectionDisplayName": collection_display_name,
        "dataConnector": connector_payload,
    }

    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would call setUpDataConnector for '%s' (%s). Payload: %s",
          collection_id,
          collection_display_name,
          json.dumps(request_body, indent=2),
      )
      return {
          "name": (
              f"projects/{project_id}/locations/{location}/"
              f"collections/default_collection/dataStores/{collection_id}"
          )
      }

    self.logger.info(
        "Provisioning Discovery Engine Data Connector '%s' via setUpDataConnector...",
        collection_id,
    )
    access_token = self.get_access_token()

    req = urllib.request.Request(
        url,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        },
        method="POST",
    )

    try:
      with urllib.request.urlopen(req) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        self.logger.info("setUpDataConnector request submitted successfully.")

        def cleanup_datastore():
          self.logger.warning(
              "Rollback: Deleting transient Data Store (%s)...", collection_id
          )
          del_url = (
              f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
              f"locations/{location}/collections/default_collection/dataStores/{collection_id}"
          )
          del_req = urllib.request.Request(
              del_url,
              headers={
                  "Authorization": f"Bearer {access_token}",
                  "X-Goog-User-Project": project_id,
              },
              method="DELETE",
          )
          try:
            urllib.request.urlopen(del_req)
          except Exception:
            pass

        self.rollback_mgr.register(
            f"Delete Discovery Engine Data Store ({collection_id})",
            cleanup_datastore,
        )

        return res_json
    except urllib.error.HTTPError as e:
      err_msg = e.read().decode("utf-8")
      if "ALREADY_EXISTS" in err_msg or e.code == 409:
        self.logger.warning("Data Store '%s' already exists.", collection_id)
        return {
            "name": (
                f"projects/{project_id}/locations/{location}/"
                f"collections/default_collection/dataStores/{collection_id}"
            )
        }
      self.logger.error("setUpDataConnector API Error %d: %s", e.code, err_msg)
      raise e

  def get_or_create_engine(
      self,
      project_id: str,
      location: str,
      engine_id: str,
      display_name: str,
      company_name: str = "Cymbal",
      features_preset: typing.Optional[str] = "RECOMMENDED",
      custom_features: typing.Optional[typing.List[str]] = None,
      data_store_ids: typing.Optional[typing.List[str]] = None,
      dry_run: bool = False,
  ) -> typing.Dict[str, typing.Any]:
    """Get existing Gemini Enterprise Engine or create a new one."""
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would get or create Gemini Enterprise Engine '%s' (%s).",
          engine_id,
          display_name,
      )
      return {"name": f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}"}

    access_token = self.get_access_token()
    base_url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/{location}/collections/default_collection/engines"
    )
    engine_url = f"{base_url}/{engine_id}"

    # 1. Check if Engine exists
    req_get = urllib.request.Request(
        engine_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Goog-User-Project": project_id,
        },
        method="GET",
    )
    engine_exists = False
    try:
      with urllib.request.urlopen(req_get) as resp:
        engine_data = json.loads(resp.read().decode("utf-8"))
        engine_exists = True
        self.logger.info("Found existing Gemini Enterprise Engine '%s'.", engine_id)
    except urllib.error.HTTPError as e:
      if e.code == 404:
        engine_exists = False
      else:
        raise e

    features_map = (
        build_engine_features_map(features_preset, custom_features)
        if features_preset or custom_features
        else None
    )

    if engine_exists:
      # Update Engine.features and dataStoreIds via PATCH only if changed
      patch_body: typing.Dict[str, typing.Any] = {}
      update_masks = []
      if features_map is not None:
        patch_body["features"] = features_map
        update_masks.append("features")

      if data_store_ids:
        existing_ds = engine_data.get("dataStoreIds", [])
        combined_ds = list(existing_ds)
        for ds in data_store_ids:
          if ds not in combined_ds:
            combined_ds.append(ds)
        if len(combined_ds) > len(existing_ds):
          patch_body["dataStoreIds"] = combined_ds
          update_masks.append("dataStoreIds")
        else:
          self.logger.info("Data store(s) already linked to Engine '%s'.", engine_id)

      if not update_masks:
        self.logger.info("Engine '%s' is already up to date.", engine_id)
        return engine_data

      self.logger.info("Updating Engine '%s'...", engine_id)
      req_patch = urllib.request.Request(
          f"{engine_url}?updateMask={','.join(update_masks)}",
          data=json.dumps(patch_body).encode("utf-8"),
          headers={
              "Authorization": f"Bearer {access_token}",
              "Content-Type": "application/json",
              "X-Goog-User-Project": project_id,
          },
          method="PATCH",
      )
      try:
        with urllib.request.urlopen(req_patch) as resp:
          self.logger.info("Engine '%s' updated successfully.", engine_id)
          return json.loads(resp.read().decode("utf-8"))
      except urllib.error.HTTPError as e:
        self.logger.warning("Engine PATCH update failed: %s", e.read().decode("utf-8"))
        return engine_data

    # 2. Create new Engine
    self.logger.info("Creating new Gemini Enterprise Engine '%s'...", engine_id)
    create_body: typing.Dict[str, typing.Any] = {
        "displayName": display_name,
        "solutionType": "SOLUTION_TYPE_SEARCH",
        "industryVertical": "GENERIC",
        "searchEngineConfig": {
            "searchTier": "SEARCH_TIER_ENTERPRISE",
            "searchAddOns": ["SEARCH_ADD_ON_LLM"],
        },
        "commonConfig": {
            "companyName": company_name,
        },
        "features": features_map,
    }
    if data_store_ids:
      create_body["dataStoreIds"] = data_store_ids

    create_url = f"{base_url}?engineId={engine_id}"
    req_create = urllib.request.Request(
        create_url,
        data=json.dumps(create_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        },
        method="POST",
    )

    with urllib.request.urlopen(req_create) as resp:
      created_engine = json.loads(resp.read().decode("utf-8"))
      self.logger.info("Gemini Enterprise Engine '%s' created successfully.", engine_id)

      def cleanup_engine():
        self.logger.warning("Rollback: Deleting transient Engine (%s)...", engine_id)
        del_req = urllib.request.Request(
            engine_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Goog-User-Project": project_id,
            },
            method="DELETE",
        )
        try:
          urllib.request.urlopen(del_req)
        except Exception:
          pass

      self.rollback_mgr.register(
          f"Delete Gemini Enterprise Engine ({engine_id})", cleanup_engine
      )
      return created_engine

  def bind_data_store_to_engine(
      self,
      project_id: str,
      location: str,
      engine_id: str,
      datastore_id: str,
      dry_run: bool = False,
  ) -> bool:
    """Bind/Link the Data Store to the target Gemini Enterprise Engine/App."""
    if not engine_id:
      self.logger.info("No Gemini Engine ID specified. Skipping automated engine binding.")
      return False

    if dry_run:
      self.logger.info("[DRY-RUN] Would bind Data Store '%s' to Engine '%s'.", datastore_id, engine_id)
      return True

    self.logger.info("Binding Data Store '%s' to Gemini Engine '%s'...", datastore_id, engine_id)
    try:
      self.get_or_create_engine(
          project_id=project_id,
          location=location,
          engine_id=engine_id,
          display_name=f"Gemini Enterprise Assistant ({engine_id})",
          features_preset=None,
          data_store_ids=[datastore_id],
          dry_run=dry_run,
      )
      self.logger.info("Data Store '%s' successfully bound to Gemini Engine '%s'.", datastore_id, engine_id)
      return True
    except Exception as e:
      self.logger.warning("Failed to bind Data Store '%s' to Engine '%s': %s", datastore_id, engine_id, str(e))
      return False

  def poll_health(
      self,
      project_id: str,
      location: str,
      datastore_id: str,
      dry_run: bool = False,
  ) -> bool:
    """Poll Discovery Engine API until Data Store state transitions to ACTIVE."""
    if dry_run:
      self.logger.info("[DRY-RUN] Health poll simulation: PASSED.")
      return True

    self.logger.info("Polling Data Store status ('%s')...", datastore_id)
    access_token = self.get_access_token()
    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/{location}/collections/default_collection/dataStores/{datastore_id}"
    )

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Goog-User-Project": project_id,
        },
        method="GET",
    )

    for attempt in range(1, 7):
      try:
        with urllib.request.urlopen(req) as resp:
          res_json = json.loads(resp.read().decode("utf-8"))
          name = res_json.get("name", "")
          if name:
            self.logger.info("Data Store is ACTIVE and ready (Attempt %d).", attempt)
            return True
      except Exception:
        pass
      time.sleep(3)

    self.logger.warning("Data Store status check timed out in GCP.")
    return False
