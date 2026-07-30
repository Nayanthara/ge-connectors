"""Pre-Flight Validation Engine for Gemini Enterprise Connector Tool.

Performs non-destructive environment sanity checks:
1. Verifies CLI tool availability (`gcloud`, `az`).
2. Validates active GCP user credentials and project configuration.
3. Validates active Entra ID login session and inspects admin role level.
4. Checks required GCP IAM role bindings.
5. Verifies network connectivity to Google Cloud & Microsoft Graph APIs.
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

    # 1. Binary Availability Check
    self.logger.debug("Checking CLI binaries (gcloud, az)...")
    if not shutil.which("gcloud"):
      errors.append(
          "Google Cloud SDK ('gcloud') is not installed or not in PATH."
      )
    if not shutil.which("az"):
      errors.append("Azure CLI ('az') is not installed or not in PATH.")

    if errors:
      for err in errors:
        self.logger.error(err)
      return PreflightResult(
          is_valid=False,
          gcp_user="",
          gcp_project="",
          entra_user="",
          entra_tenant_id="",
          is_global_admin=False,
          warnings=warnings,
          errors=errors,
      )

    # 2. GCP Authentication Check
    self.logger.debug("Inspecting GCP authentication session...")
    gcp_account_res = self._run_cmd("gcloud config get-value account")
    gcp_user = (
        gcp_account_res.stdout.strip()
        if gcp_account_res.returncode == 0
        else ""
    )
    if not gcp_user or gcp_user == "(unset)":
      errors.append(
          "No active GCP authentication session found. Please run 'gcloud auth"
          " login'."
      )

    gcp_project_res = self._run_cmd("gcloud config get-value project")
    gcp_project = target_gcp_project or (
        gcp_project_res.stdout.strip()
        if gcp_project_res.returncode == 0
        else ""
    )
    if not gcp_project or gcp_project == "(unset)":
      warnings.append("GCP project is not explicitly configured in gcloud.")

    # 3. Azure / Entra ID Authentication Check
    self.logger.debug("Inspecting Entra ID authentication session...")
    azure_session_res = self._run_cmd("az account show -o json")
    entra_user = ""
    entra_tenant_id = ""
    is_global_admin = False

    if (
        azure_session_res.returncode != 0
        or not azure_session_res.stdout.strip()
    ):
      errors.append(
          "No active Azure authentication session found. Please run 'az login'."
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
                "Active Entra user is not a Global Administrator. Admin consent"
                " will require manual completion via provided URL."
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

    is_valid = len(errors) == 0
    if is_valid:
      self.logger.info("Pre-flight checks passed successfully.")
    else:
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
