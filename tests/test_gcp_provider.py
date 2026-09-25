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


def test_bind_data_store_to_engine_empty_id():
  """Verify bind_data_store_to_engine skips when engine_id is empty."""
  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)

  res = provider.bind_data_store_to_engine(
      project_id="proj", location="global", engine_id="", datastore_id="ds1"
  )
  assert res is False


def test_bind_data_store_to_engine_dry_run():
  """Verify bind_data_store_to_engine in dry_run mode."""
  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)

  res = provider.bind_data_store_to_engine(
      project_id="proj",
      location="global",
      engine_id="eng1",
      datastore_id="ds1",
      dry_run=True,
  )
  assert res is True


def test_bind_data_store_to_engine_already_linked(monkeypatch):
  """Verify bind_data_store_to_engine when dataStore is already linked."""
  import json
  from unittest.mock import MagicMock

  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)
  monkeypatch.setattr(provider, "get_access_token", lambda: "fake-token")

  engine_payload = json.dumps({
      "name": "projects/proj/locations/global/collections/default_collection/engines/eng1",
      "dataStoreIds": ["ds1", "ds2"],
  }).encode("utf-8")

  mock_resp = MagicMock()
  mock_resp.read.return_value = engine_payload
  mock_resp.__enter__.return_value = mock_resp

  monkeypatch.setattr("urllib.request.urlopen", lambda req: mock_resp)

  res = provider.bind_data_store_to_engine(
      project_id="proj",
      location="global",
      engine_id="eng1",
      datastore_id="ds1",
  )
  assert res is True


def test_bind_data_store_to_engine_patches_datastore_ids(monkeypatch):
  """Verify bind_data_store_to_engine patches dataStoreIds when not yet linked."""
  import json
  from unittest.mock import MagicMock

  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)
  monkeypatch.setattr(provider, "get_access_token", lambda: "fake-token")

  engine_payload = json.dumps({
      "name": "projects/proj/locations/global/collections/default_collection/engines/eng1",
      "dataStoreIds": ["ds1"],
  }).encode("utf-8")

  captured_requests = []

  def fake_urlopen(req):
    captured_requests.append(req)
    mock_resp = MagicMock()
    mock_resp.read.return_value = engine_payload
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp

  monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

  res = provider.bind_data_store_to_engine(
      project_id="proj",
      location="global",
      engine_id="eng1",
      datastore_id="ds2",
  )
  assert res is True
  assert len(captured_requests) == 2
  # First request was GET
  assert captured_requests[0].get_method() == "GET"
  # Second request was PATCH with updateMask=dataStoreIds
  patch_req = captured_requests[1]
  assert patch_req.get_method() == "PATCH"
  assert "updateMask=dataStoreIds" in patch_req.full_url
  body = json.loads(patch_req.data.decode("utf-8"))
  assert body["dataStoreIds"] == ["ds1", "ds2"]


def test_bind_data_store_to_engine_creates_if_not_found(monkeypatch):
  """Verify bind_data_store_to_engine calls get_or_create_engine when 404."""
  import urllib.error
  from unittest.mock import MagicMock

  logger = logging.getLogger("test")
  rollback_mgr = RollbackManager(logger=logger)
  provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)
  monkeypatch.setattr(provider, "get_access_token", lambda: "fake-token")

  def fake_urlopen(req):
    raise urllib.error.HTTPError(
        url="http://fake",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=MagicMock(read=lambda: b"Not Found"),
    )

  monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
  created_engines = []
  monkeypatch.setattr(
      provider,
      "get_or_create_engine",
      lambda **kwargs: created_engines.append(kwargs) or {"name": "created"},
  )

  res = provider.bind_data_store_to_engine(
      project_id="proj",
      location="global",
      engine_id="eng1",
      datastore_id="ds1",
  )
  assert res is True
  assert len(created_engines) == 1
  assert created_engines[0]["engine_id"] == "eng1"
  assert created_engines[0]["data_store_ids"] == ["ds1"]


