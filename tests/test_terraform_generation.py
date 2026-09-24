"""Unit tests for Terraform generation in Gemini Enterprise Connector Tool."""

import json
import os
import shutil
import tempfile
import unittest

from core.logger import setup_logger
from core.rollback import RollbackManager
from plugins.custom_mcp import CustomMcpPlugin
from plugins.onedrive import OneDrivePlugin
from plugins.outlook import OutlookPlugin
from plugins.sharepoint import SharePointPlugin
from plugins.teams import TeamsPlugin


class TestTerraformGeneration(unittest.TestCase):
  """Tests for Terraform file generation and template integrity across all connectors."""

  def setUp(self):
    self.logger = setup_logger(verbose=False)
    self.rollback_mgr = RollbackManager(logger=self.logger)
    self.test_dir = tempfile.mkdtemp(prefix="ge_tf_test_")

  def tearDown(self):
    if os.path.exists(self.test_dir):
      shutil.rmtree(self.test_dir)

  def test_sharepoint_terraform_generation(self):
    plugin = SharePointPlugin(self.logger, None, None, self.rollback_mgr)
    config = {
        "gcp_project": "test-project-12345",
        "location": "global",
        "mode": "FEDERATED",
        "access_level": "READ_WRITE",
        "o365_env": "com",
        "instance_uri": "https://test-tenant.sharepoint.com",
        "entra_tenant_id": "11111111-2222-3333-4444-555555555555",
        "existing_client_id": None,
        "cmek_kms_key": None,
        "engine_id": "test-engine-id",
        "datastore_id": "test-sharepoint-ds",
    }
    out_dir = os.path.join(self.test_dir, "sharepoint")
    generated_files = plugin.generate_terraform(config, output_dir=out_dir)
    self.assertTrue(len(generated_files) >= 7)

    for fpath in generated_files:
      with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
      self.assertNotIn("__", content, f"Found unreplaced placeholder in {os.path.basename(fpath)}")

  def test_onedrive_terraform_generation(self):
    plugin = OneDrivePlugin(self.logger, None, None, self.rollback_mgr)
    config = {
        "gcp_project": "test-project-12345",
        "location": "global",
        "mode": "FEDERATED",
        "access_level": "READ_WRITE",
        "o365_env": "com",
        "instance_uri": "https://test-my.sharepoint.com",
        "entra_tenant_id": "11111111-2222-3333-4444-555555555555",
        "existing_client_id": None,
        "cmek_kms_key": None,
        "engine_id": "test-engine-id",
        "datastore_id": "test-onedrive-ds",
    }
    out_dir = os.path.join(self.test_dir, "onedrive")
    generated_files = plugin.generate_terraform(config, output_dir=out_dir)
    self.assertTrue(len(generated_files) >= 7)

    for fpath in generated_files:
      with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
      self.assertNotIn("__", content, f"Found unreplaced placeholder in {os.path.basename(fpath)}")

  def test_outlook_terraform_generation(self):
    plugin = OutlookPlugin(self.logger, None, None, self.rollback_mgr)
    config = {
        "gcp_project": "test-project-12345",
        "location": "global",
        "mode": "FEDERATED",
        "access_level": "READ_WRITE",
        "o365_env": "com",
        "entra_tenant_id": "11111111-2222-3333-4444-555555555555",
        "existing_client_id": None,
        "cmek_kms_key": None,
        "engine_id": "test-engine-id",
        "datastore_id": "test-outlook-ds",
    }
    out_dir = os.path.join(self.test_dir, "outlook")
    generated_files = plugin.generate_terraform(config, output_dir=out_dir)
    self.assertTrue(len(generated_files) >= 7)

    for fpath in generated_files:
      with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
      self.assertNotIn("__", content, f"Found unreplaced placeholder in {os.path.basename(fpath)}")

  def test_teams_terraform_generation(self):
    plugin = TeamsPlugin(self.logger, None, None, self.rollback_mgr)
    config = {
        "gcp_project": "test-project-12345",
        "location": "global",
        "mode": "FEDERATED",
        "access_level": "READ_WRITE",
        "entra_tenant_id": "11111111-2222-3333-4444-555555555555",
        "tenant_domain": "tenant.onmicrosoft.com",
        "existing_client_id": None,
        "cmek_kms_key": None,
        "engine_id": "test-engine-id",
        "datastore_id": "test-teams-ds",
    }
    out_dir = os.path.join(self.test_dir, "teams")
    generated_files = plugin.generate_terraform(config, output_dir=out_dir)
    self.assertTrue(len(generated_files) >= 7)

    for fpath in generated_files:
      with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
      self.assertNotIn("__", content, f"Found unreplaced placeholder in {os.path.basename(fpath)}")

  def test_custom_mcp_terraform_generation(self):
    plugin = CustomMcpPlugin(self.logger, None, None, self.rollback_mgr)
    config = {
        "gcp_project": "test-project-12345",
        "location": "global",
        "mcp_url": "https://service-12345.us-central1.run.app/mcp",
        "entra_tenant_id": "11111111-2222-3333-4444-555555555555",
        "existing_client_id": None,
        "cmek_kms_key": None,
        "engine_id": "test-engine-id",
        "datastore_id": "test-custom-mcp-ds",
    }
    out_dir = os.path.join(self.test_dir, "custom_mcp")
    generated_files = plugin.generate_terraform(config, output_dir=out_dir)
    self.assertTrue(len(generated_files) >= 7)

    for fpath in generated_files:
      with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
      self.assertNotIn("__", content, f"Found unreplaced placeholder in {os.path.basename(fpath)}")
