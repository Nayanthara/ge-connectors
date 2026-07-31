"""Pre-Flight Validation Engine for Gemini Enterprise Connector Tool.

Performs non-destructive environment sanity checks:
1. Verifies CLI tool availability (`gcloud`, `az`).
2. Validates active GCP user credentials, project, and IAM role permissions.
3. Automatically attempts to self-grant missing GCP IAM roles if the user has
IAM Admin privileges.
4. Validates active Entra ID login session and inspects admin role level.
"""

import json
import logging
import shutil
import subprocess
import typing


class PreflightResult(typing.NamedTuple):
  """Encapsulates the pre-flight check outcomes."""

  is_valid: bool
  gcp_user: str
  gcp_project: str
  entra_user: str
  entra_tenant_id: str
  is_global_admin: bool
  warnings: typing.List[str]
  errors: typing.List[str]


class PreflightValidator:
  """Non-destructive validation runner that inspects system state."""

  def __init__(self, logger: logging.Logger):
    self.logger = logger

  def _run_cmd(self, cmd: str) -> subprocess.CompletedProcess[str]:
    """Helper to run a shell command silently."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, check=False
    )

  def _try_auto_grant_role(
      self, project_id: str, gcp_user: str, role: str
  ) -> bool:
    """Attempt to self-grant an IAM role if user has project IAM admin rights."""
    self.logger.info(
        "Attempting to automatically self-grant role '%s' to '%s' on project"
        " '%s'...",
        role,
        gcp_user,
        project_id,
    )
    grant_cmd = (
        f"gcloud projects add-iam-policy-binding {project_id} "
        f'--member="user:{gcp_user}" --role="{role}" --quiet'
    )
    res = self._run_cmd(grant_cmd)
    if res.returncode == 0:
      self.logger.info(
          "Successfully auto-granted missing role '%s' to '%s'.",
          role,
          gcp_user,
      )
      return True
    self.logger.warning(
        "Auto-grant for role '%s' failed (insufficient IAM Admin rights).",
        role,
    )
    return False

  def _check_gcp_permission(self, project_id: str, permission: str) -> bool:
    """Test if active user holds a specific GCP permission via testIamPermissions API."""
    test_cmd = (
        f"gcloud rest --method POST --url"
        f" 'https://secretmanager.googleapis.com/v1/projects/{project_id}:testIamPermissions'"
        f' --body=\'{{"permissions":["{permission}"]}}\' -o json'
    )
    res = self._run_cmd(test_cmd)
    if res.returncode == 0 and res.stdout.strip():
      try:
        data = json.loads(res.stdout)
        granted = data.get("permissions", [])
        return permission in granted
      except Exception:  # pylint: disable=broad-exception-caught
        return False
    return False

  def validate(
      self, target_gcp_project: typing.Optional[str] = None
  ) -> PreflightResult:
    """Run all pre-flight checks and return a structured summary.

    Args:
      target_gcp_project: Optional GCP Project ID to validate against.

    Returns:
      PreflightResult object containing validation flags and metadata.
    """
    self.logger.info("Starting Pre-Flight Environment Sanity Checks...")
    errors: typing.List[str] = []
    warnings: typing.List[str] = []

    gcp_user = ""
    gcp_project = ""
    entra_user = ""
    entra_tenant_id = ""
    is_global_admin = False

    # 1. Binary Availability Check
    self.logger.debug("Checking CLI binaries (gcloud, az)...")
    has_gcloud = bool(shutil.which("gcloud"))
    has_az = bool(shutil.which("az"))

    if not has_gcloud:
      errors.append(
          "Google Cloud SDK ('gcloud') is not installed or not in PATH."
      )

    if not has_az:
      errors.append("Azure CLI ('az') is not installed or not in PATH.")
      warnings.append(
          "Install Azure CLI by running: curl -sL"
          " https://aka.ms/InstallAzureCLIDeb | sudo bash"
      )

    # 2. GCP Authentication & IAM Permission Check
    if has_gcloud:
      self.logger.debug("Inspecting GCP authentication session...")
      gcp_account_res = self._run_cmd("gcloud config get-value account")
      gcp_user = (
          gcp_account_res.stdout.strip()
          if gcp_account_res.returncode == 0
          else ""
      )
      if not gcp_user or gcp_user == "(unset)":
        errors.append(
            "No active GCP authentication session found. Please run"
            " 'gcloud auth login'."
        )

      gcp_project_res = self._run_cmd("gcloud config get-value project")
      gcp_project = target_gcp_project or (
          gcp_project_res.stdout.strip()
          if gcp_project_res.returncode == 0
          else ""
      )
      if not gcp_project or gcp_project == "(unset)":
        warnings.append(
            "GCP project is not explicitly configured in gcloud. Set it by"
            " running: gcloud config set project YOUR_PROJECT_ID"
        )
      elif gcp_user:
        # Check GCP IAM Permissions on target project
        self.logger.debug(
            "Inspecting GCP IAM permissions for user '%s' on project '%s'...",
            gcp_user,
            gcp_project,
        )

        has_sm = self._check_gcp_permission(
            gcp_project, "secretmanager.secrets.create"
        )

        # Fallback to get-iam-policy if testIamPermissions REST API is
        # unavailable
        if not has_sm:
          iam_res = self._run_cmd(
              f"gcloud projects get-iam-policy {gcp_project} -o json"
          )
          if iam_res.returncode == 0 and iam_res.stdout.strip():
            try:
              iam_data = json.loads(iam_res.stdout)
              user_member = f"user:{gcp_user}"
              roles_found = [
                  binding.get("role", "")
                  for binding in iam_data.get("bindings", [])
                  if user_member in binding.get("members", [])
              ]
              has_owner = "roles/owner" in roles_found
              has_sm = (
                  has_owner
                  or "roles/secretmanager.admin" in roles_found
                  or "roles/secretmanager.editor" in roles_found
                  or "roles/editor" in roles_found
              )
            except Exception:  # pylint: disable=broad-exception-caught
              pass

        if not has_sm:
          # Attempt automated self-grant first (editor role then admin role)
          if self._try_auto_grant_role(
              gcp_project, gcp_user, "roles/secretmanager.editor"
          ) or self._try_auto_grant_role(
              gcp_project, gcp_user, "roles/secretmanager.admin"
          ):
            has_sm = True
          else:
            errors.append(
                f"Account '{gcp_user}' lacks Secret Manager creation"
                f" permission on project '{gcp_project}' and could not"
                " self-grant the role."
            )
            warnings.append(
                f"Ask a Project IAM Admin to run: gcloud projects"
                f" add-iam-policy-binding {gcp_project}"
                f' --member="user:{gcp_user}"'
                ' --role="roles/secretmanager.editor"'
            )

    # 3. Azure / Entra ID Authentication Check (only if az is installed)
    if has_az:
      self.logger.debug("Inspecting Entra ID authentication session...")
      azure_session_res = self._run_cmd("az account show -o json")

      if (
          azure_session_res.returncode != 0
          or not azure_session_res.stdout.strip()
      ):
        errors.append(
            "No active Azure authentication session found. Please run 'az login"
            " --use-device-code --allow-no-subscriptions'."
        )
      else:
        try:
          az_data = json.loads(azure_session_res.stdout)
          entra_tenant_id = az_data.get("tenantId", "")
          entra_user = az_data.get("user", {}).get("name", "Azure User")

          # Check Entra Admin Roles (Global Admin vs Cloud App Admin)
          self.logger.debug(
              "Inspecting Entra ID administrator roles for active user..."
          )
          roles_cmd = (
              "az rest --method GET --url"
              " 'https://graph.microsoft.com/v1.0/me/memberOf' -o json"
          )
          roles_res = self._run_cmd(roles_cmd)
          if roles_res.returncode == 0 and roles_res.stdout.strip():
            groups_data = json.loads(roles_res.stdout)
            role_names = [
                item.get("displayName", "")
                for item in groups_data.get("value", [])
                if item.get("@odata.type") == "#microsoft.graph.directoryRole"
            ]
            if "Global Administrator" in role_names:
              is_global_admin = True
              self.logger.info(
                  "Entra ID Role: Global Administrator (Automatic Admin Consent"
                  " Enabled)."
              )
            elif (
                "Cloud Application Administrator" in role_names
                or "Application Developer" in role_names
            ):
              self.logger.info(
                  "Entra ID Role: Cloud Application Administrator (Manual Admin"
                  " Consent Guidance Mode)."
              )
              warnings.append(
                  "Active Entra user is not a Global Administrator. Admin"
                  " consent will require manual completion via provided URL."
              )
            else:
              warnings.append(
                  "Could not verify specific Entra administrative roles for the"
                  " active user."
              )
        except Exception as e:  # pylint: disable=broad-exception-caught
          warnings.append(
              f"Failed to inspect detailed Entra ID directory roles: {str(e)}"
          )

    # 4. Final Result Reporting
    is_valid = len(errors) == 0
    if is_valid:
      self.logger.info("Pre-flight checks passed successfully.")
    else:
      for err in errors:
        self.logger.error(err)
      for warn in warnings:
        self.logger.info("[TIP] %s", warn)
      self.logger.error(
          "Pre-flight checks failed with %d error(s).", len(errors)
      )

    return PreflightResult(
        is_valid=is_valid,
        gcp_user=gcp_user,
        gcp_project=gcp_project,
        entra_user=entra_user,
        entra_tenant_id=entra_tenant_id,
        is_global_admin=is_global_admin,
        warnings=warnings,
        errors=errors,
    )
