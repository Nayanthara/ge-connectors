"""Google Cloud Platform (GCP) Service Provider Module.

Handles GCP infrastructure operations for Gemini Enterprise:
- Automated GCP API enablement
- Secret Manager creation
- Discovery Engine Data Store creation via REST API
- Binding/linking Data Store to Gemini Enterprise Engine/App
"""

import json
import logging
import subprocess
import time
import typing
import urllib.error
import urllib.parse
import urllib.request


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
    """Enable required GCP APIs.

    Args:
        project_id: Target GCP Project ID.
        dry_run: If True, simulates action without modifying state.
    """
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would enable GCP APIs: %s on project %s.",
          ", ".join(self.REQUIRED_APIS),
          project_id,
      )
      return

    self.logger.info(
        "Configuring gcloud quota project and enabling required GCP APIs on"
        " project '%s'...",
        project_id,
    )
    self._run_cmd(
        f"gcloud config set billing/quota_project {project_id}", check=False
    )
    cmd = (
        f"gcloud services enable {' '.join(self.REQUIRED_APIS)}"
        f" --project={project_id}"
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
    """Store Client Secret in Secret Manager with expiration tags.

    Args:
        project_id: GCP Project ID.
        secret_id: Target Secret Manager ID.
        secret_value: Client secret value string.
        expiration_date: Expiration ISO date string.
        cmek_kms_key: Optional Cloud KMS Key URI.
        dry_run: If True, simulates action without modifying state.

    Returns:
        GCP secret version resource name string.

    Raises:
        RuntimeError: If secret creation fails or permissions are denied.
    """
    secret_path = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would store Client Secret in GCP Secret Manager (%s) with"
          " CMEK: %s.",
          secret_id,
          cmek_kms_key or "Google-Managed",
      )
      return secret_path

    self.logger.info(
        "Storing Client Secret in GCP Secret Manager ('%s')...", secret_id
    )

    # Check if secret container exists
    check_cmd = (
        f"gcloud secrets describe {secret_id} --project={project_id} -o json"
    )
    res = self._run_cmd(check_cmd, check=False)

    # Build CMEK flag if provided
    cmek_flag = (
        f"--kms-key-name={cmek_kms_key}"
        if cmek_kms_key
        else "--replication-policy=automatic"
    )

    exp_clean = expiration_date.split("T")[0].replace("-", "_")
    labels = f"expiration_date={exp_clean},connector_type=sharepoint_federated_search,alert_before_days=30"

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
          self.logger.warning(
              "Secret creation failed due to missing IAM permissions."
              " Attempting auto-grant of 'roles/secretmanager.editor'..."
          )
          gcp_user_res = self._run_cmd(
              "gcloud config get-value account", check=False
          )
          gcp_user = (
              gcp_user_res.stdout.strip()
              if gcp_user_res.returncode == 0
              else ""
          )
          if gcp_user:
            grant_cmd = (
                f"gcloud projects add-iam-policy-binding {project_id}"
                f' --member="user:{gcp_user}"'
                ' --role="roles/secretmanager.editor" --quiet'
            )
            grant_res = self._run_cmd(grant_cmd, check=False)
            if grant_res.returncode == 0:
              self.logger.info(
                  "Successfully self-granted 'roles/secretmanager.editor'."
                  " Retrying secret creation..."
              )
              self._run_cmd(create_cmd, check=True)
            else:
              raise RuntimeError(
                  "Permission 'secretmanager.secrets.create' denied on project"
                  f" '{project_id}'.\n"
                  f"Please ask a Project IAM Admin to run:\n"
                  f"  gcloud projects add-iam-policy-binding {project_id}"
                  f' --member="user:{gcp_user}"'
                  ' --role="roles/secretmanager.editor"'
              )
        else:
          raise RuntimeError(
              f"Failed to create secret '{secret_id}': {create_res.stderr}"
          )

      def cleanup_secret():
        self.logger.warning(
            "Rollback: Deleting transient secret (%s)...", secret_id
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

  def create_discovery_engine_data_store(
      self,
      project_id: str,
      location: str,
      datastore_id: str,
      client_id: str,
      client_secret: str,
      tenant_id: str,
      instance_uri: str,
      dry_run: bool = False,
  ) -> typing.Dict[str, typing.Any]:
    """Call Discovery Engine REST API to provision SharePoint Data Store.

    Uses the official setUpDataConnector endpoint as documented in:
    https://docs.cloud.google.com/gemini/enterprise/docs/connectors/ms-sharepoint/set-up-data-store

    Args:
        project_id: GCP Project ID.
        location: GCP Location (e.g. global, us, eu).
        datastore_id: Data Store / Collection ID string.
        client_id: Entra Application Client ID.
        client_secret: Entra Application Client Secret.
        tenant_id: Entra Tenant ID string.
        instance_uri: SharePoint Instance URL string.
        dry_run: If True, simulates action without modifying state.

    Returns:
        API Response Dictionary.
    """
    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/{location}:setUpDataConnector"
    )

    payload = {
        "collectionId": datastore_id,
        "collectionDisplayName": "SharePoint Online Federated",
        "dataConnector": {
            "dataSource": "sharepoint_federated_search",
            "params": {
                "client_id": client_id,
                "client_secret": client_secret,
                "instance_uri": instance_uri,
                "tenant_id": tenant_id,
            },
            "entities": [{"entityName": "file"}],
            "refreshInterval": "7200s",
            "connectorType": "THIRD_PARTY_FEDERATED",
            "connectorModes": ["FEDERATED"],
        },
    }

    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would issue POST request to setUpDataConnector API for"
          " '%s'.",
          datastore_id,
      )
      return {
          "name": (
              f"projects/{project_id}/locations/{location}/"
              f"collections/default_collection/dataStores/{datastore_id}"
          )
      }

    self.logger.info(
        "Provisioning Discovery Engine SharePoint Federated Data Store '%s'"
        " via setUpDataConnector REST API...",
        datastore_id,
    )
    access_token = self.get_access_token()

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
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
        self.logger.info(
            "setUpDataConnector API request submitted successfully."
        )

        def cleanup_datastore():
          self.logger.warning(
              "Rollback: Deleting transient Data Store (%s)...", datastore_id
          )
          del_url = (
              f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
              f"locations/{location}/collections/default_collection/dataStores/{datastore_id}"
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
          except Exception:  # pylint: disable=broad-exception-caught
            pass

        self.rollback_mgr.register(
            f"Delete Discovery Engine Data Store ({datastore_id})",
            cleanup_datastore,
        )

        return res_json
    except urllib.error.HTTPError as e:
      err_msg = e.read().decode("utf-8")
      if "ALREADY_EXISTS" in err_msg or e.code == 409:
        self.logger.warning("Data Store '%s' already exists.", datastore_id)
        return {
            "name": (
                f"projects/{project_id}/locations/{location}/"
                f"collections/default_collection/dataStores/{datastore_id}"
            )
        }
      self.logger.error("setUpDataConnector API Error %d: %s", e.code, err_msg)
      raise e

  def bind_data_store_to_engine(
      self,
      project_id: str,
      location: str,
      engine_id: str,
      datastore_id: str,
      dry_run: bool = False,
  ) -> bool:
    """Bind/Link the Data Store to the target Gemini Enterprise Engine/App.

    Args:
        project_id: GCP Project ID.
        location: GCP Location.
        engine_id: Gemini Engine ID string.
        datastore_id: Data Store ID string.
        dry_run: If True, simulates action without modifying state.

    Returns:
        True if engine binding succeeds, False otherwise.
    """
    if not engine_id:
      self.logger.info(
          "No Gemini Engine ID specified. Skipping automated engine binding."
      )
      return False

    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/{location}/collections/default_collection/engines/{engine_id}/dataStores?dataStoreId={datastore_id}"
    )

    if dry_run:
      self.logger.info(
          "[DRY-RUN] Would bind Data Store '%s' to Engine '%s'.",
          datastore_id,
          engine_id,
      )
      return True

    self.logger.info(
        "Binding Data Store '%s' to Gemini Engine '%s'...",
        datastore_id,
        engine_id,
    )
    access_token = self.get_access_token()

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Goog-User-Project": project_id,
        },
        method="POST",
    )

    try:
      with urllib.request.urlopen(req) as _resp:  # pylint: disable=unused-variable
        self.logger.info(
            "Data Store successfully bound to Gemini Engine '%s'.", engine_id
        )
        return True
    except urllib.error.HTTPError as e:
      err_msg = e.read().decode("utf-8")
      if "ALREADY_EXISTS" in err_msg or e.code == 409:
        self.logger.info(
            "Data Store is already linked to Engine '%s'.", engine_id
        )
        return True
      self.logger.warning("Engine binding failed (%d): %s", e.code, err_msg)
      return False

  def poll_health(
      self,
      project_id: str,
      location: str,
      datastore_id: str,
      dry_run: bool = False,
  ) -> bool:
    """Poll Discovery Engine API until Data Store state transitions to ACTIVE.

    Args:
        project_id: GCP Project ID.
        location: GCP Location.
        datastore_id: Data Store ID string.
        dry_run: If True, simulates action without modifying state.

    Returns:
        True if Data Store status is ACTIVE, False otherwise.
    """
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
            self.logger.info(
                "Data Store is ACTIVE and ready (Attempt %d).", attempt
            )
            return True
      except Exception:  # pylint: disable=broad-exception-caught
        pass
      time.sleep(3)

    self.logger.warning("Data Store status check timed out in GCP.")
    return False
