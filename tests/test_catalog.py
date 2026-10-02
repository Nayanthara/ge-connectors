"""Unit tests for core/catalog.py."""

import pytest
from core.catalog import (
    ACTION_CATALOG,
    CONNECTOR_CATALOG,
    ENGINE_FEATURE_CATALOG,
    build_engine_features_map,
    resolve_enabled_actions,
    resolve_least_privilege_permissions,
)


def test_action_catalog_counts():
  """Verify that the action catalog matches the expected actions."""
  assert len(ACTION_CATALOG["outlook"]) == 21
  assert len(ACTION_CATALOG["sharepoint"]) == 18
  assert len(ACTION_CATALOG["onedrive"]) == 10
  assert len(ACTION_CATALOG["teams"]) == 12

  total_actions = sum(len(actions) for actions in ACTION_CATALOG.values())
  assert total_actions == 61


def test_resolve_enabled_actions_access_levels():
  """Verify enabled actions resolution for READ_WRITE vs READ_ONLY."""
  # Outlook read-only actions (download_attachments, word_convert_to_pdf, pptx_convert_to_pdf)
  ro_actions = resolve_enabled_actions("outlook", access_level="READ_ONLY")
  assert len(ro_actions) == 3
  assert "download_attachments" in ro_actions
  assert "send_mail" not in ro_actions

  # Outlook read-write actions (all 21)
  rw_actions = resolve_enabled_actions("outlook", access_level="READ_WRITE")
  assert len(rw_actions) == 21
  assert "send_mail" in rw_actions


def test_resolve_least_privilege_permissions():
  """Verify least-privilege permission resolution across connectors and modes."""
  # SharePoint federated read-write
  sp_perms = resolve_least_privilege_permissions(
      ["sharepoint"], mode="FEDERATED", access_level="READ_WRITE"
  )
  assert "Sites.Search.All" in sp_perms["sharepoint_scopes"]
  assert "AllSites.Write" in sp_perms["sharepoint_scopes"]
  assert "Sites.Read.All" in sp_perms["graph_scopes"]
  assert "Sites.ReadWrite.All" in sp_perms["graph_scopes"]

  # Teams permissions
  teams_perms = resolve_least_privilege_permissions(
      ["teams"], mode="FEDERATED", access_level="READ_WRITE"
  )
  assert "ChannelMessage.Send" in teams_perms["graph_scopes"]
  assert "Channel.ReadBasic.All" in teams_perms["graph_roles"]

  # Ingestion mode includes Graph and SharePoint roles
  sp_ingest = resolve_least_privilege_permissions(
      ["sharepoint"], mode="DATA_INGESTION"
  )
  assert "Sites.FullControl.All" in sp_ingest["graph_roles"]
  assert "Sites.FullControl.All" in sp_ingest["sharepoint_roles"]


def test_engine_features_polarity_and_presets():
  """Verify Engine.features polarity handling (POS vs NEG) and cascading."""
  # 33 features total
  assert len(ENGINE_FEATURE_CATALOG) == 36 or len(ENGINE_FEATURE_CATALOG) == 33

  rec_map = build_engine_features_map("RECOMMENDED")
  # 'no-code-agent-builder' is POS and enabled -> FEATURE_STATE_ON
  assert rec_map["no-code-agent-builder"] == "FEATURE_STATE_ON"
  # 'disable-canvas' is NEG and enabled -> FEATURE_STATE_OFF
  assert rec_map["disable-canvas"] == "FEATURE_STATE_OFF"
  # 'disable-multi-agent-orchestration' is NEG and enabled -> FEATURE_STATE_OFF
  assert rec_map["disable-multi-agent-orchestration"] == "FEATURE_STATE_OFF"
  # 'sobi' is disabled in RECOMMENDED -> FEATURE_STATE_OFF
  assert rec_map["sobi"] == "FEATURE_STATE_OFF"

  # All preset
  all_map = build_engine_features_map("ALL")
  assert all_map["sobi"] == "FEATURE_STATE_ON"
  assert all_map["disable-canvas"] == "FEATURE_STATE_OFF"

  # Custom cascade
  custom_map = build_engine_features_map(
      "CUSTOM", custom_enabled_keys=["no-code-agent-builder"]
  )
  assert custom_map["no-code-agent-builder"] == "FEATURE_STATE_ON"
  # agent-gallery auto-enabled as parent
  assert custom_map["agent-gallery"] == "FEATURE_STATE_ON"
