"""Unit tests for plugins (sharepoint, onedrive, outlook, teams, custom_mcp)."""

import logging
from unittest.mock import MagicMock
from core.rollback import RollbackManager
from plugins.custom_mcp import CustomMcpPlugin
from plugins.onedrive import OneDrivePlugin
from plugins.outlook import OutlookPlugin
from plugins.sharepoint import SharePointPlugin
from plugins.teams import TeamsPlugin


def create_mock_providers():
  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  entra_provider = MagicMock()
  gcp_provider = MagicMock()
  return logger, entra_provider, gcp_provider, rollback_mgr


def test_sharepoint_plugin_dry_run_and_validate():
  logger, entra_p, gcp_p, rb_mgr = create_mock_providers()
  plugin = SharePointPlugin(logger, entra_p, gcp_p, rb_mgr)

  # Validation test
  errs = plugin.validate_config({})
  assert len(errs) >= 2

  valid_config = {
      "gcp_project": "proj-1",
      "entra_tenant_id": "tenant-1",
      "instance_uri": "https://tenant.sharepoint.com",
      "mode": "FEDERATED",
      "access_level": "READ_WRITE",
  }
  assert len(plugin.validate_config(valid_config)) == 0

  res = plugin.provision(valid_config, dry_run=True)
  assert res["client_id"] == "DRY_RUN_CLIENT_ID"
  assert "sharepoint-ds" in res["datastore_id"]


def test_onedrive_plugin_dry_run_and_validate():
  logger, entra_p, gcp_p, rb_mgr = create_mock_providers()
  plugin = OneDrivePlugin(logger, entra_p, gcp_p, rb_mgr)

  valid_config = {
      "gcp_project": "proj-1",
      "entra_tenant_id": "tenant-1",
      "instance_uri": "https://tenant-my.sharepoint.com",
      "mode": "FEDERATED",
  }
  assert len(plugin.validate_config(valid_config)) == 0

  res = plugin.provision(valid_config, dry_run=True)
  assert res["client_id"] == "DRY_RUN_CLIENT_ID"
  assert "onedrive-ds" in res["datastore_id"]


def test_outlook_plugin_dry_run_and_validate():
  logger, entra_p, gcp_p, rb_mgr = create_mock_providers()
  plugin = OutlookPlugin(logger, entra_p, gcp_p, rb_mgr)

  valid_config = {
      "gcp_project": "proj-1",
      "entra_tenant_id": "tenant-1",
      "mode": "FEDERATED",
  }
  assert len(plugin.validate_config(valid_config)) == 0

  res = plugin.provision(valid_config, dry_run=True)
  assert res["client_id"] == "DRY_RUN_CLIENT_ID"
  assert "outlook-ds" in res["datastore_id"]


def test_teams_plugin_dry_run_and_validate():
  logger, entra_p, gcp_p, rb_mgr = create_mock_providers()
  plugin = TeamsPlugin(logger, entra_p, gcp_p, rb_mgr)

  valid_config = {
      "gcp_project": "proj-1",
      "entra_tenant_id": "tenant-1",
      "mode": "FEDERATED",
  }
  assert len(plugin.validate_config(valid_config)) == 0

  res = plugin.provision(valid_config, dry_run=True)
  assert res["client_id"] == "DRY_RUN_CLIENT_ID"
  assert "teams-ds" in res["datastore_id"]


def test_custom_mcp_plugin_dry_run_and_validate():
  logger, entra_p, gcp_p, rb_mgr = create_mock_providers()
  plugin = CustomMcpPlugin(logger, entra_p, gcp_p, rb_mgr)

  valid_config = {
      "gcp_project": "proj-1",
      "entra_tenant_id": "tenant-1",
      "mcp_url": "https://service-12345.us-central1.run.app/mcp",
  }
  assert len(plugin.validate_config(valid_config)) == 0

  res = plugin.provision(valid_config, dry_run=True)
  assert res["client_id"] == "DRY_RUN_CLIENT_ID"
  assert "ms-custom-mcp-connector" in res["datastore_id"]

