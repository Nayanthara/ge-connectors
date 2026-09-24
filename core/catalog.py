"""Catalog definitions for Gemini Enterprise Connectors, Actions, and Engine Features.

Contains authoritative mappings for:
1. Supported Connectors & Data Source configurations.
2. 61 BAP Actions Catalog (SharePoint, OneDrive, Outlook, Teams).
3. Least-Privilege Entra ID Permission Matrix (Graph & SharePoint UUIDs, Roles, Scopes).
4. 33 Gemini Enterprise Engine.features Catalog with polarity handling (POS vs NEG).
"""

from typing import Any, Dict, List, Optional, Set, Tuple

# Base delegated scopes required for any Entra ID 3LO integration
BASE_DELEGATED_SCOPES = [
    "User.Read",
    "openid",
    "profile",
    "offline_access",
]

# Standard OAuth redirect URIs for Google Cloud Gemini Enterprise / Discovery Engine
GEMINI_ENTERPRISE_REDIRECT_URIS = [
    "https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html",
    "https://vertexaisearch.cloud.google.com/oauth-redirect",
    "https://vertexaisearch.cloud.google.com/console/oauth/generic_oauth.html",
]

# Well-known Microsoft Service Principal Application IDs
MICROSOFT_GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"
SHAREPOINT_ONLINE_APP_ID = "00000003-0000-0ff1-ce00-000000000000"

# Connector Metadata Catalog
CONNECTOR_CATALOG: Dict[str, Dict[str, Any]] = {
    "sharepoint": {
        "display_name": "Microsoft SharePoint Online",
        "data_source": "sharepoint",
        "default_collection_id": "microsoft-sharepoint",
        "default_refresh_interval": "7200s",
        "entities": ["file", "page", "comment", "event", "attachment"],
        "supports_ingestion": True,
        "supports_federated": True,
    },
    "onedrive": {
        "display_name": "Microsoft OneDrive",
        "data_source": "onedrive",
        "default_collection_id": "microsoft-onedrive",
        "default_refresh_interval": "86400s",
        "entities": ["file"],
        "supports_ingestion": True,
        "supports_federated": True,
    },
    "outlook": {
        "display_name": "Microsoft Outlook (Mail, Calendar, Contacts)",
        "data_source": "outlook",
        "default_collection_id": "microsoft-outlook",
        "default_refresh_interval": "7200s",
        "entities": ["mail", "mail-attachment", "calendar", "contact"],
        "supports_ingestion": True,
        "supports_federated": True,
    },
    "teams": {
        "display_name": "Microsoft Teams",
        "data_source": "teams",
        "default_collection_id": "microsoft-teams",
        "default_refresh_interval": "7200s",
        "entities": ["team", "channel", "channel-message", "channel-file"],
        "supports_ingestion": True,
        "supports_federated": True,
    },
    "custom_mcp": {
        "display_name": "Microsoft Custom MCP Actions",
        "data_source": "custom_mcp",
        "default_collection_id": "ms-custom-mcp-connector",
        "default_refresh_interval": "7200s",
        "entities": [],
        "supports_ingestion": False,
        "supports_federated": True,
    },
}

# 61 BAP Actions Catalog: action_id -> (display_name, is_read_only)
ACTION_CATALOG: Dict[str, Dict[str, Tuple[str, bool]]] = {
    "outlook": {
        "send_mail": ("Send email", False),
        "forward_mail": ("Forward email", False),
        "move_mail": ("Move email", False),
        "add_attachments": ("Add attachments to draft", False),
        "download_attachments": ("Download email attachments", True),
        "create_event": ("Create calendar event", False),
        "update_event": ("Update calendar event", False),
        "rsvp_to_event": ("RSVP to calendar invitation", False),
        "create_calendar": ("Create calendar", False),
        "update_calendar": ("Update calendar", False),
        "create_contact": ("Create contact", False),
        "update_contact": ("Update contact", False),
        "word_create_document": ("Create Word document", False),
        "word_convert_to_pdf": ("Convert Word document to PDF", True),
        "pptx_create_presentation": ("Create PowerPoint presentation", False),
        "pptx_convert_to_pdf": ("Convert PowerPoint to PDF", True),
        "excel_create_table": ("Create Excel table", False),
        "excel_create_worksheet": ("Create Excel worksheet", False),
        "excel_add_row_to_table": ("Add row to Excel table", False),
        "excel_update_row": ("Update Excel table row", False),
        "excel_add_key_column": ("Add key column to Excel table", False),
    },
    "sharepoint": {
        "list_lists": ("List SharePoint lists & libraries", True),
        "get_list_item": ("Get SharePoint list item", True),
        "get_list_fields": ("Get SharePoint list schema/fields", True),
        "create_folder": ("Create folder in SharePoint", False),
        "add_page": ("Create SharePoint page", False),
        "update_page": ("Update SharePoint page", False),
        "upload_document": ("Upload document to SharePoint", False),
        "update_file_properties": ("Update file metadata properties", False),
        "move_attachment_or_document": ("Move attachment or document", False),
        "rename_attachment_or_document": ("Rename attachment or document", False),
        "check_in_document": ("Check in document", False),
        "check_out_document": ("Check out document", False),
        "discard_check_out_document": ("Discard document checkout", False),
        "add_list": ("Create SharePoint list", False),
        "update_list": ("Update SharePoint list", False),
        "create_list_item": ("Create SharePoint list item", False),
        "update_list_item": ("Update SharePoint list item", False),
        "share_resource": ("Share document, folder, or site", False),
    },
    "onedrive": {
        "upload_file": ("Upload file to OneDrive", False),
        "create_folder": ("Create folder in OneDrive", False),
        "copy_file": ("Copy file in OneDrive", False),
        "copy_folder": ("Copy folder in OneDrive", False),
        "move_file": ("Move file in OneDrive", False),
        "move_folder": ("Move folder in OneDrive", False),
        "rename_file": ("Rename file in OneDrive", False),
        "rename_folder": ("Rename folder in OneDrive", False),
        "update_file_properties": ("Update file metadata properties", False),
        "share_file_folder": ("Create sharing link for file/folder", False),
    },
    "teams": {
        "send_channel_message": ("Send message to Teams channel", False),
        "update_channel_message": ("Update Teams channel message", False),
        "send_chat_message": ("Send message in Teams chat", False),
        "update_chat_message": ("Update Teams chat message", False),
        "create_channel": ("Create new Teams channel", False),
        "update_channel": ("Update Teams channel properties", False),
        "add_member_to_channel": ("Add member to Teams channel", False),
        "create_chat": ("Create new Teams chat thread", False),
        "update_chat": ("Update Teams chat properties", False),
        "create_schedule": ("Create Teams shift schedule", False),
        "create_time_off_entry": ("Create Teams time-off entry", False),
        "update_time_off_entry": ("Update Teams time-off entry", False),
    },
}

# 33 Gemini Enterprise Engine.features Catalog
# Each tuple: (key, label, default_enabled_in_recommended, polarity)
# polarity:
#   POS: enabled -> "FEATURE_STATE_ON", disabled -> "FEATURE_STATE_OFF"
#   NEG: enabled -> "FEATURE_STATE_OFF", disabled -> "FEATURE_STATE_ON" (opposite logic for disable-* keys)
ENGINE_FEATURE_CATALOG: List[Tuple[str, str, bool, str]] = [
    # 1. Agents
    ("agent-gallery", "Agents: Agent Gallery — /agents entry point", True, "POS"),
    ("no-code-agent-builder", "Agents: Chat Agents (No-Code Builder)", True, "POS"),
    ("workflow-agents", "Agents: Workflow Agents (AgentFlow Designer v2)", True, "POS"),
    ("disable-single-agent-orchestration", "Agents: Single-Agent Orchestration", True, "NEG"),
    ("disable-multi-agent-orchestration", "Agents: Multi-Agent Orchestration", True, "NEG"),
    ("prompt-gallery", "Agents: Prompt Gallery", True, "POS"),
    ("disable-agent-sharing", "Agents: Agent Sharing", True, "NEG"),
    ("agent-sharing-without-admin-approval", "Agents: Share Agents Without Admin Approval", True, "POS"),
    ("enable-end-user-sharing-with-groups", "Agents: Share Agents With Groups", True, "POS"),
    ("skills", "Agents: Skills in Web App", True, "POS"),
    ("skill-sharing", "Agents: Skill Sharing", True, "POS"),
    ("skill-sharing-without-admin-approval", "Agents: Share Skills Without Admin Approval", True, "POS"),
    ("disable-projects", "Agents: Dedicated Projects Workspaces", True, "NEG"),
    ("sobi", "Agents: Conversational Analytics (SOBI)", False, "POS"),

    # 2. Content & Integrations
    ("notebook-lm", "Content: NotebookLM / Gemini Notebook", True, "POS"),
    ("disable-canvas", "Content: Canvas Side-by-Side Editor", True, "NEG"),
    ("canvas-workspace", "Content: Canvas Workspace", True, "POS"),
    ("canvas-app-builder", "Content: Canvas App Builder", True, "POS"),
    ("disable-onedrive-upload", "Content: OneDrive File Upload", True, "NEG"),
    ("disable-google-drive-upload", "Content: Google Drive File Upload", True, "NEG"),
    ("disable-talk-to-content", "Content: Grounded Q&A Over Documents", True, "NEG"),

    # 3. Models & Media Generation
    ("model-selector", "Models: Model Selector Dropdown", True, "POS"),
    ("disable-image-generation", "Models: Image Generation (Imagen)", True, "NEG"),
    ("disable-video-generation", "Models: Video Generation (Veo)", True, "NEG"),

    # 4. Platform, Voice & Personalization
    ("personalization-memory", "Platform: Cross-Session User Memory", True, "POS"),
    ("personalization-suggested-highlights", "Platform: Suggested Prompt Cards", True, "POS"),
    ("session-sharing", "Platform: Read-Only Session Sharing", True, "POS"),
    ("people-search", "Platform: People & Directory Search", True, "POS"),
    ("people-search-org-chart", "Platform: Org Chart in People Search", True, "POS"),
    ("in-app-notifications", "Platform: In-App Notifications", True, "POS"),
    ("mobile-app-access", "Platform: Mobile App Access", True, "POS"),
    ("speech-to-text", "Platform: Speech-to-Text Microphone Dictation", True, "POS"),
    ("bi-directional-audio", "Platform: Gemini Live Bi-Directional Audio", False, "POS"),
    ("disable-welcome-emails", "Platform: Onboarding Welcome Emails", True, "NEG"),
    ("feedback", "Platform: Response Quality Feedback", True, "POS"),
    ("cross-product-intelligence", "Platform: Workspace & Data Cloud Context Sharing", False, "POS"),
]


def resolve_least_privilege_permissions(
    connectors: List[str],
    mode: str = "FEDERATED",
    access_level: str = "READ_WRITE",
) -> Dict[str, List[str]]:
  """Resolve least-privilege Entra ID permissions for given connectors, mode, and access tier.

  Args:
      connectors: List of connector keys (e.g. ['sharepoint', 'teams']).
      mode: 'FEDERATED' or 'DATA_INGESTION' or 'ALL'.
      access_level: 'READ_WRITE', 'READ_ONLY', or 'CUSTOM'.

  Returns:
      Dict with keys:
          'graph_roles': Application permissions for Microsoft Graph.
          'graph_scopes': Delegated permissions for Microsoft Graph.
          'sharepoint_roles': Application permissions for SharePoint API.
          'sharepoint_scopes': Delegated permissions for SharePoint API.
  """
  mode_upper = mode.upper()
  is_ingestion = mode_upper in ("DATA_INGESTION", "INGESTION", "ALL")
  is_federated = mode_upper in ("FEDERATED", "ALL")
  is_read_only = access_level.upper() == "READ_ONLY"

  graph_roles: Set[str] = set()
  graph_scopes: Set[str] = set(BASE_DELEGATED_SCOPES)
  sp_roles: Set[str] = set()
  sp_scopes: Set[str] = set()

  for conn in connectors:
    conn_key = conn.lower()
    if conn_key == "sharepoint":
      if is_ingestion:
        graph_roles.update([
            "Sites.Read.All",
            "Sites.FullControl.All",
            "Files.Read.All",
            "User.Read.All",
            "Group.Read.All",
            "GroupMember.Read.All",
        ])
        sp_roles.update(["Sites.FullControl.All", "Sites.Read.All"])
      if is_federated:
        graph_roles.update([
            "Sites.Read.All",
            "Files.Read.All",
            "User.Read.All",
            "Group.Read.All",
            "GroupMember.Read.All",
        ])
        graph_scopes.update([
            "Sites.Read.All",
            "Files.Read.All",
            "User.Read",
            "User.Read.All",
            "User.ReadBasic.All",
            "GroupMember.Read.All",
        ])
        sp_scopes.update(["AllSites.Read", "Sites.Search.All"])
        if not is_read_only:
          graph_scopes.update([
              "Sites.ReadWrite.All",
              "Sites.Manage.All",
              "Files.ReadWrite",
              "Files.ReadWrite.All",
          ])
          sp_scopes.update(["AllSites.Write", "AllSites.FullControl"])

    elif conn_key == "onedrive":
      if is_ingestion:
        graph_roles.update([
            "Files.Read.All",
            "Sites.Read.All",
            "Sites.FullControl.All",
            "User.Read.All",
            "Group.Read.All",
            "GroupMember.Read.All",
        ])
      if is_federated:
        graph_roles.update([
            "Files.Read.All",
            "Sites.Read.All",
            "User.Read.All",
            "Group.Read.All",
            "GroupMember.Read.All",
        ])
        graph_scopes.update([
            "Files.Read.All",
            "Sites.Read.All",
            "User.Read",
            "User.Read.All",
            "User.ReadBasic.All",
            "Group.Read.All",
            "GroupMember.Read.All",
        ])
        if not is_read_only:
          graph_scopes.update([
              "Files.ReadWrite",
              "Files.ReadWrite.All",
              "Files.ReadWrite.AppFolder",
          ])

    elif conn_key == "outlook":
      if is_ingestion:
        graph_roles.update([
            "Mail.Read",
            "Mail.ReadBasic",
            "Mail.ReadBasic.All",
            "Calendars.Read",
            "Calendars.ReadBasic.All",
            "Contacts.Read",
            "User.Read.All",
            "User.ReadBasic.All",
            "Group.Read.All",
        ])
      if is_federated:
        graph_roles.update([
            "Mail.Read",
            "Calendars.Read",
            "Contacts.Read",
            "User.Read.All",
        ])
        graph_scopes.update([
            "Mail.Read",
            "Mail.Read.Shared",
            "Mail.ReadBasic",
            "Calendars.Read",
            "Contacts.Read",
            "Files.Read.All",
            "User.Read",
            "User.Read.All",
            "User.ReadBasic.All",
        ])
        if not is_read_only:
          graph_scopes.update([
              "Mail.ReadWrite",
              "Mail.Send",
              "Calendars.ReadWrite",
              "Contacts.ReadWrite",
              "Tasks.ReadWrite",
              "Files.ReadWrite",
              "Files.ReadWrite.All",
          ])

    elif conn_key == "teams":
      graph_roles.update([
          "Channel.ReadBasic.All",
          "ChannelMember.Read.All",
          "ChannelMessage.Read.All",
          "Chat.Read.All",
          "Group.Read.All",
          "Schedule.Read.All",
          "Team.ReadBasic.All",
          "TeamMember.Read.All",
          "User.Read.All",
      ])
      graph_scopes.update([
          "Channel.ReadBasic.All",
          "ChannelMember.Read.All",
          "ChannelMessage.Read.All",
          "Chat.Read",
          "Chat.ReadBasic",
          "ChatMessage.Read",
          "Group.Read.All",
          "Schedule.Read.All",
          "Team.ReadBasic.All",
          "TeamMember.Read.All",
          "User.Read",
          "User.Read.All",
      ])
      if not is_read_only:
        graph_scopes.update([
            "Channel.Create",
            "ChannelMember.ReadWrite.All",
            "ChannelMessage.ReadWrite",
            "ChannelMessage.Send",
            "ChannelSettings.ReadWrite.All",
            "Chat.Create",
            "Chat.ReadWrite",
            "ChatMessage.Send",
            "Schedule.ReadWrite.All",
        ])

    elif conn_key == "custom_mcp":
      graph_scopes.add("User.Read")

  return {
      "graph_roles": sorted(list(graph_roles)),
      "graph_scopes": sorted(list(graph_scopes)),
      "sharepoint_roles": sorted(list(sp_roles)),
      "sharepoint_scopes": sorted(list(sp_scopes)),
  }


def resolve_enabled_actions(
    connector_source: str,
    access_level: str = "READ_WRITE",
    selected_actions: Optional[List[str]] = None,
) -> List[str]:
  """Resolve enabled actions list for a connector source."""
  catalog = ACTION_CATALOG.get(connector_source, {})
  if not catalog:
    return []

  if selected_actions is not None:
    return [a for a in selected_actions if a in catalog]

  if access_level.upper() == "READ_ONLY":
    return [aid for aid, (_, is_ro) in catalog.items() if is_ro]

  # Default: READ_WRITE (all supported actions)
  return list(catalog.keys())


def build_engine_features_map(
    features_preset: str = "RECOMMENDED",
    custom_enabled_keys: Optional[List[str]] = None,
) -> Dict[str, str]:
  """Build the Engine.features dictionary with proper polarity handling.

  Args:
      features_preset: 'RECOMMENDED', 'ALL', or 'CUSTOM'.
      custom_enabled_keys: Optional list of keys if CUSTOM preset is used.

  Returns:
      Dict mapping each feature key to 'FEATURE_STATE_ON' or 'FEATURE_STATE_OFF'.
  """
  enabled_keys_set: Set[str] = set()

  if features_preset.upper() == "ALL":
    enabled_keys_set = {f[0] for f in ENGINE_FEATURE_CATALOG}
  elif features_preset.upper() == "RECOMMENDED":
    enabled_keys_set = {f[0] for f in ENGINE_FEATURE_CATALOG if f[2]}
  elif features_preset.upper() == "CUSTOM" and custom_enabled_keys:
    enabled_keys_set = set(custom_enabled_keys)
  else:
    enabled_keys_set = {f[0] for f in ENGINE_FEATURE_CATALOG if f[2]}

  # Cascade dependencies
  if "no-code-agent-builder" in enabled_keys_set or "workflow-agents" in enabled_keys_set:
    enabled_keys_set.add("agent-gallery")
  if "skill-sharing" in enabled_keys_set or "skill-sharing-without-admin-approval" in enabled_keys_set:
    enabled_keys_set.add("skills")
  if "skill-sharing-without-admin-approval" in enabled_keys_set:
    enabled_keys_set.add("skill-sharing")
  if "agent-sharing-without-admin-approval" in enabled_keys_set or "enable-end-user-sharing-with-groups" in enabled_keys_set:
    enabled_keys_set.add("disable-agent-sharing")
  if "canvas-workspace" in enabled_keys_set or "canvas-app-builder" in enabled_keys_set:
    enabled_keys_set.add("disable-canvas")
  if "personalization-suggested-highlights" in enabled_keys_set:
    enabled_keys_set.add("personalization-memory")

  feature_map: Dict[str, str] = {}
  for key, _, _, polarity in ENGINE_FEATURE_CATALOG:
    is_active = key in enabled_keys_set
    if polarity == "NEG":
      # Inverted logic: active means 'disable-*' is OFF
      feature_map[key] = "FEATURE_STATE_OFF" if is_active else "FEATURE_STATE_ON"
    else:
      feature_map[key] = "FEATURE_STATE_ON" if is_active else "FEATURE_STATE_OFF"

  return feature_map

