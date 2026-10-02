"""Unit tests for providers/gcp_provider.py."""

import logging
from core.rollback import RollbackManager
from providers.gcp_provider import GcpProvider


def test_build_bap_connector_payload_federated():
  """Verify BAP payload construction for FEDERATED mode with actions."""
  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)

  params = {"client_id": "cid", "tenant_id": "tid", "instance_uri": "https://tenant.sharepoint.com"}
  action_params = {"client_id": "cid", "client_secret": "sec", "tenant_id": "tid"}
  entities = [{"entityName": "file"}]

  payload = provider.build_bap_connector_payload(
      data_source="sharepoint",
      mode="FEDERATED",
      params=params,
      action_params=action_params,
      entities=entities,
  )

  assert payload["dataSource"] == "sharepoint"
  assert payload["connectorModes"] == ["FEDERATED", "ACTIONS"]
  assert payload["aclEnabled"] is False
  assert payload["actionConfig"]["createBapConnection"] is True
  assert "enabledActions" in payload["bapConfig"]
  assert len(payload["bapConfig"]["enabledActions"]) == 18


def test_build_bap_connector_payload_ingestion():
  """Verify BAP payload construction for DATA_INGESTION mode."""
  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)

  params = {"client_id": "cid", "tenant_id": "tid", "instance_uri": "https://tenant.sharepoint.com"}
  action_params = {"client_id": "cid", "client_secret": "sec"}
  entities = [{"entityName": "file"}]

  payload = provider.build_bap_connector_payload(
      data_source="sharepoint",
      mode="DATA_INGESTION",
      params=params,
      action_params=action_params,
      entities=entities,
  )

  assert payload["dataSource"] == "sharepoint"
  assert payload["connectorModes"] == ["DATA_CONNECTOR"]
  assert payload["aclEnabled"] is True
  assert "enabledActions" not in payload["bapConfig"]

