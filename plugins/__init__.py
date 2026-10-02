"""Connector Plugins Package for Gemini Enterprise Connector Tool."""

from plugins.custom_mcp import CustomMcpPlugin
from plugins.onedrive import OneDrivePlugin
from plugins.outlook import OutlookPlugin
from plugins.sharepoint import SharePointPlugin
from plugins.teams import TeamsPlugin

__all__ = [
    "SharePointPlugin",
    "OneDrivePlugin",
    "OutlookPlugin",
    "TeamsPlugin",
    "CustomMcpPlugin",
]
