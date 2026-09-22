"""Unit tests for Terraform generation in Gemini Enterprise Connector Tool."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from plugins.sharepoint_federated import SharePointFederatedPlugin
from core.logger import setup_logger
from core.rollback import RollbackManager


class TestTerraformGeneration(unittest.TestCase):
  """Tests for Terraform file generation and template integrity."""

  def setUp(self):
    self.logger = setup_logger(verbose=False)
    self.rollback_mgr = RollbackManager(logger=self.logger)
    self.plugin = SharePointFederatedPlugin(
        logger=self.logger,
        entra_provider=None,
        gcp_provider=None,
        rollback_mgr=self.rollback_mgr,
    )
    self.test_dir = tempfile.mkdtemp(prefix="ge_tf_test_")
    self.sample_config = {
        "gcp_project": "test-project-12345",
        "location": "global",
        "instance_uri": "https://test-tenant.sharepoint.com",
        "entra_tenant_id": "11111111-2222-3333-4444-555555555555",
        "existing_client_id": None,
        "cmek_kms_key": None,
        "engine_id": "test-engine-id",
        "datastore_id": "test-sharepoint-ds",
        "is_global_admin": False,
    }

  def tearDown(self):
    if os.path.exists(self.test_dir):
      shutil.rmtree(self.test_dir)

  def test_generate_terraform_files_created(self):
    """Test that all required Terraform files are generated."""
    generated_files = self.plugin.generate_terraform(
        self.sample_config, output_dir=self.test_dir
    )
    expected_filenames = [
        "README.md",
        "azuread.tf",
        "discovery_engine.tf",
        "gcp_secret_manager.tf",
        "outputs.tf",
        "providers.tf",
        "terraform.tfvars",
        "variables.tf",
    ]
    created_filenames = sorted(
        [os.path.basename(f) for f in generated_files]
    )
    self.assertEqual(created_filenames, expected_filenames)

  def test_variable_substitution_in_tfvars(self):
    """Test that placeholders are properly substituted in terraform.tfvars."""
    self.plugin.generate_terraform(
        self.sample_config, output_dir=self.test_dir
    )
    tfvars_path = os.path.join(self.test_dir, "terraform.tfvars")
    self.assertTrue(os.path.exists(tfvars_path))

    with open(tfvars_path, "r", encoding="utf-8") as f:
      content = f.read()

    self.assertIn('gcp_project        = "test-project-12345"', content)
    self.assertIn('instance_uri       = "https://test-tenant.sharepoint.com"', content)
    self.assertIn('entra_tenant_id    = "11111111-2222-3333-4444-555555555555"', content)
    self.assertIn('datastore_id       = "test-sharepoint-ds"', content)
    self.assertIn('engine_id          = "test-engine-id"', content)
    self.assertIn("cmek_kms_key       = null", content)
    self.assertIn("existing_client_id = null", content)
    self.assertNotIn("__GCP_PROJECT__", content)

  def test_no_unreplaced_placeholders(self):
    """Ensure no unrendered __PLACEHOLDER__ tokens remain in any output file."""
    generated_files = self.plugin.generate_terraform(
        self.sample_config, output_dir=self.test_dir
    )
    for file_path in generated_files:
      with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
      self.assertNotIn(
          "__",
          content,
          f"Found unreplaced placeholder in {os.path.basename(file_path)}",
      )

  def test_terraform_validate_if_installed(self):
    """Run terraform init and terraform validate if terraform CLI binary is present."""
    if not shutil.which("terraform"):
      self.skipTest("terraform binary is not installed in local environment")

    self.plugin.generate_terraform(
        self.sample_config, output_dir=self.test_dir
    )
    init_res = subprocess.run(
        ["terraform", "init", "-backend=false"],
        cwd=self.test_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    self.assertEqual(
        init_res.returncode,
        0,
        f"terraform init failed:\n{init_res.stderr}\n{init_res.stdout}",
    )

    validate_res = subprocess.run(
        ["terraform", "validate"],
        cwd=self.test_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    self.assertEqual(
        validate_res.returncode,
        0,
        f"terraform validate failed:\n{validate_res.stderr}\n{validate_res.stdout}",
    )


if __name__ == "__main__":
  unittest.main()
