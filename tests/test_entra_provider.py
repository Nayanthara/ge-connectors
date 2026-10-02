"""Unit tests for providers/entra_provider.py."""

import logging
from unittest.mock import MagicMock
from core.rollback import RollbackManager
from providers.entra_provider import EntraProvider


def test_build_resource_access_payload():
  """Verify that build_resource_access_payload generates valid Graph and SharePoint accesses."""
  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  provider = EntraProvider(logger=logger, rollback_mgr=rollback_mgr)

  # Mock _query_sp_manifest to return empty so fallback static map is used
  provider._query_sp_manifest = MagicMock(return_value={})

  payload = provider.build_resource_access_payload(
      connectors=["sharepoint", "teams"],
      mode="FEDERATED",
      access_level="READ_WRITE",
  )

  assert len(payload) == 2
  app_ids = {p["resourceAppId"] for p in payload}
  assert provider.GRAPH_APP_ID in app_ids
  assert provider.SHAREPOINT_APP_ID in app_ids

  # Ensure items have 'id' and 'type'
  for p in payload:
    for item in p["resourceAccess"]:
      assert "id" in item
      assert item["type"] in ("Scope", "Role")

