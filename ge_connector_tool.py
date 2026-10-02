#!/usr/bin/env python3
"""Gemini Enterprise 3P Connector Automation Tool.

Enterprise CLI tool for provisioning and configuring 3P data connectors
(SharePoint, OneDrive, Outlook, Teams, Custom MCP) for Gemini Enterprise
(Discovery Engine) on Google Cloud.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

# Ensure local packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# pylint: disable=g-import-not-at-top
from core.logger import setup_logger
from core.preflight import PreflightValidator
from core.rollback import RollbackManager
from plugins.custom_mcp import CustomMcpPlugin
from plugins.onedrive import OneDrivePlugin
from plugins.outlook import OutlookPlugin
from plugins.sharepoint import SharePointPlugin
from plugins.teams import TeamsPlugin
from providers.entra_provider import EntraProvider
from providers.gcp_provider import GcpProvider


def parse_args() -> argparse.Namespace:
  """Parse command-line arguments."""
  parser = argparse.ArgumentParser(
      description="Gemini Enterprise 3P Connector Automation Tool",
      formatter_class=argparse.RawTextHelpFormatter,
  )
  parser.add_argument(
      "--connector",
      type=str,
      default="sharepoint",
      help=(
          "Connector(s) to provision (default: sharepoint).\n"
          "Options: sharepoint, onedrive, outlook, teams, custom_mcp, all,\n"
          "or comma-separated list (e.g. sharepoint,onedrive,outlook)"
      ),
  )
  parser.add_argument(
      "--mode",
      type=str,
      default="FEDERATED",
      choices=["FEDERATED", "DATA_INGESTION"],
      help="Connector architecture mode (default: FEDERATED)",
  )
  parser.add_argument(
      "--access-level",
      type=str,
      default="READ_WRITE",
      choices=["READ_WRITE", "READ_ONLY"],
      help="Action execution permission tier (default: READ_WRITE)",
  )
  parser.add_argument(
      "--engine-features",
      type=str,
      default="RECOMMENDED",
      help="App features preset (RECOMMENDED, ALL, CUSTOM) or comma-separated keys",
  )
  parser.add_argument(
      "--o365-env",
      type=str,
      default="com",
      help="Microsoft 365 cloud environment TLD suffix: 'com' (default), 'us', or custom",
  )
  parser.add_argument(
      "--mcp-url",
      type=str,
      default="",
      help="Custom MCP Server URL (for custom_mcp connector)",
  )
  parser.add_argument(
      "--engine-id",
      type=str,
      default="",
      help="Gemini Enterprise App/Engine ID to bind to",
  )
  parser.add_argument(
      "-p",
      "--project",
      type=str,
      default="",
      help="GCP Project ID override",
  )
  parser.add_argument(
      "-l",
      "--location",
      type=str,
      default="",
      help="Discovery Engine location (default: global)",
  )
  parser.add_argument(
      "--tenant-id",
      type=str,
      default="",
      help="Microsoft Entra ID Tenant ID override",
  )
  parser.add_argument(
      "--client-id",
      type=str,
      default="",
      help="Existing Microsoft Entra ID Application (Client) ID",
  )
  parser.add_argument(
      "--config",
      type=str,
      default="",
      help="Path to JSON configuration file for non-interactive execution",
  )
  parser.add_argument(
      "--dry-run",
      action="store_true",
      help="Simulate execution, validate permissions, and render proposed change plan",
  )
  parser.add_argument(
      "--interactive",
      action="store_true",
      default=True,
      help="Run interactive wizard prompts (default: True unless --config is supplied)",
  )
  parser.add_argument(
      "--terraform",
      action="store_true",
      default=False,
      help="Generate Terraform configuration files instead of directly provisioning",
  )
  parser.add_argument(
      "--output-dir",
      type=str,
      default="terraform_output",
      help="Target directory for generated Terraform files (default: terraform_output)",
  )
  parser.add_argument(
      "--verbose",
      action="store_true",
      help="Enable detailed DEBUG logging output",
  )
  return parser.parse_args()


def print_banner() -> None:
  """Print ANSI stylized welcome banner."""
  banner = """
\033[1m\033[96m========================================================================
             GEMINI ENTERPRISE 3P CONNECTOR AUTOMATION TOOL
========================================================================\033[0m
"""
  print(banner)


def resolve_requested_connectors(conn_arg: str, available: List[str]) -> List[str]:
  """Resolve comma-separated or 'all' connector input into valid connector keys."""
  cleaned = conn_arg.strip().lower()
  if cleaned == "all":
    return [c for c in available if c != "custom_mcp"]
  items = [c.strip() for c in cleaned.split(",") if c.strip()]
  resolved = []
  for item in items:
    if item in available and item not in resolved:
      resolved.append(item)
  return resolved


def main() -> None:
  """Main Orchestrator Entry Point."""
  args = parse_args()
  logger = setup_logger(verbose=args.verbose)
  print_banner()

  rollback_mgr = RollbackManager(logger=logger)
  preflight = PreflightValidator(logger=logger)

  # 1. Run Pre-flight Checks
  pf_res = preflight.validate()
  if not pf_res.is_valid:
    if args.terraform or args.dry_run:
      logger.warning(
          "Pre-flight validation reported issues, but proceeding with %s mode.",
          "Terraform" if args.terraform else "Dry-Run",
      )
    else:
      logger.error("Pre-flight validation failed. Correct the errors above and re-run.")
      sys.exit(1)

  for warning in pf_res.warnings:
    logger.warning("Pre-flight Warning: %s", warning)

  # 2. Instantiate Cloud Service Providers
  entra_provider = EntraProvider(logger=logger, rollback_mgr=rollback_mgr)
  gcp_provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)

  # 3. Instantiate Available Plugins
  sp_plugin = SharePointPlugin(logger, entra_provider, gcp_provider, rollback_mgr)
  od_plugin = OneDrivePlugin(logger, entra_provider, gcp_provider, rollback_mgr)
  ol_plugin = OutlookPlugin(logger, entra_provider, gcp_provider, rollback_mgr)
  tm_plugin = TeamsPlugin(logger, entra_provider, gcp_provider, rollback_mgr)
  mcp_plugin = CustomMcpPlugin(logger, entra_provider, gcp_provider, rollback_mgr)

  plugin_registry = {
      "sharepoint": sp_plugin,
      "onedrive": od_plugin,
      "outlook": ol_plugin,
      "teams": tm_plugin,
      "custom_mcp": mcp_plugin,
  }

  target_connectors = resolve_requested_connectors(args.connector, list(plugin_registry.keys()))
  if not target_connectors:
    logger.error(
        "No valid connectors requested via '%s'. Available: %s",
        args.connector,
        list(plugin_registry.keys()),
    )
    sys.exit(1)

  logger.info("Target Connector(s): %s", ", ".join(target_connectors))

  # 4. Gather or load configuration
  defaults = {
      "gcp_project": args.project or pf_res.gcp_project,
      "location": args.location or "global",
      "entra_tenant_id": args.tenant_id or pf_res.entra_tenant_id,
      "existing_client_id": args.client_id or None,
      "is_global_admin": pf_res.is_global_admin,
      "mode": args.mode,
      "access_level": args.access_level,
      "o365_env": args.o365_env,
      "engine_id": args.engine_id,
      "mcp_url": args.mcp_url,
  }

  loaded_config: Dict[str, Any] = {}
  if args.config:
    logger.info("Loading configuration file '%s'...", args.config)
    try:
      with open(args.config, "r", encoding="utf-8") as f:
        loaded_config = json.load(f)
      loaded_config["is_global_admin"] = pf_res.is_global_admin
    except Exception as e:
      logger.error("Failed to read config file '%s': %s", args.config, str(e))
      sys.exit(1)

  # 5. Process each connector
  provision_reports = []
  provision_results = []

  for conn_key in target_connectors:
    plugin = plugin_registry[conn_key]
    logger.info("--- Processing Connector: %s (%s) ---", plugin.name, plugin.connector_type)

    if loaded_config:
      conn_config = {k: v for k, v in loaded_config.items() if not isinstance(v, dict)}
      if conn_key in loaded_config and isinstance(loaded_config[conn_key], dict):
        conn_config.update(loaded_config[conn_key])
      conn_config["is_global_admin"] = pf_res.is_global_admin
      conn_config["mode"] = conn_config.get("mode", args.mode)
      conn_config["access_level"] = conn_config.get("access_level", args.access_level)
      conn_config["o365_env"] = conn_config.get("o365_env", args.o365_env)
      if args.project:
        conn_config["gcp_project"] = args.project
      if args.location:
        conn_config["location"] = args.location
      if args.tenant_id:
        conn_config["entra_tenant_id"] = args.tenant_id
      if args.client_id:
        conn_config["existing_client_id"] = args.client_id
      if args.engine_id and not conn_config.get("engine_id"):
        conn_config["engine_id"] = args.engine_id
      if args.mcp_url and not conn_config.get("mcp_url"):
        conn_config["mcp_url"] = args.mcp_url
    else:
      conn_config = plugin.prompt_config_interactive(defaults)

    # Validate
    validation_errors = plugin.validate_config(conn_config)
    if validation_errors:
      for err in validation_errors:
        logger.error("[%s] Config Error: %s", conn_key, err)
      sys.exit(1)

    # Terraform Mode
    if args.terraform:
      out_dir = (
          os.path.join(args.output_dir, conn_key)
          if len(target_connectors) > 1
          else args.output_dir
      )
      logger.info("Generating Terraform files for %s in '%s'...", conn_key, out_dir)
      generated_files = plugin.generate_terraform(conn_config, output_dir=out_dir)
      provision_reports.append(
          f"Terraform ({conn_key}): Generated {len(generated_files)} files in {out_dir}"
      )
      continue

    # Dry-Run Mode
    if args.dry_run:
      logger.info("Executing [%s] in DRY-RUN mode...", conn_key)
      plugin.provision(conn_config, dry_run=True)
      provision_reports.append(f"Dry-Run ({conn_key}): Validated successfully")
      continue

    # Real Provisioning
    try:
      logger.info("Initiating provisioning for [%s]...", conn_key)
      provision_res = plugin.provision(conn_config, dry_run=False)
      provision_results.append(provision_res)
      is_healthy = plugin.verify(conn_config, provision_res)
      provision_reports.append(
          f"Provisioned ({conn_key}): DataStore='{provision_res['datastore_id']}' ClientId='{provision_res['client_id']}' Active={is_healthy}"
      )
    except Exception as e:
      logger.critical("Provisioning [%s] aborted due to error: %s", conn_key, str(e))
      rollback_mgr.execute_rollback()
      sys.exit(1)

  # 6. Disable rollback on success
  if not args.dry_run and not args.terraform:
    rollback_mgr.disable()

    # Configure Engine features if an engine was targeted
    target_engine_id = args.engine_id or loaded_config.get("engine_id")
    if target_engine_id:
      logger.info(
          "Configuring Engine.features for Engine '%s' (Preset: %s)...",
          target_engine_id,
          args.engine_features,
      )
      gcp_provider.get_or_create_engine(
          project_id=defaults["gcp_project"],
          location=loaded_config.get("location", "global"),
          engine_id=target_engine_id,
          display_name=f"Gemini Enterprise Assistant ({target_engine_id})",
          features_preset=args.engine_features,
      )

  # 7. Print Final Summary Report
  report_header = [
      "\n\033[1m\033[92m========================================================================",
      "                OPERATION COMPLETED SUCCESSFULLY!",
      "========================================================================\033[0m",
  ]
  print("\n".join(report_header))
  for rep in provision_reports:
    print(f"  • {rep}")

  if not args.dry_run and not args.terraform and provision_results:
    print("\n\033[1m\033[96m========================================================================")
    print("                 POST-SETUP: USER AUTHORIZATION GUIDANCE")
    print("========================================================================\033[0m")

    gcp_proj = defaults.get("gcp_project", "YOUR_PROJECT_ID")
    for res in provision_results:
      cid = res.get("client_id")
      ds_id = res.get("datastore_id")
      consent = res.get("admin_consent_granted", False)

      print(f"\nConnector DataStore: \033[1m{ds_id}\033[0m")
      if consent:
        print("  • Admin Consent: \033[92mTenant-wide consent automatically approved.\033[0m")
      else:
        print("  • Admin Consent: \033[93mManual approval required (non-Global Admin session).\033[0m")
        print(f"    1. Open Entra Portal: https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/{cid}")
        print("    2. Click 'Grant admin consent for <tenant>'.")

      print("  • Gemini Enterprise Authorization:")
      print(f"    1. Open GE Console: https://console.cloud.google.com/gen-app-builder/data-stores?project={gcp_proj}")
      print(f"    2. Select Data Store '{ds_id}' and click 'Authorize'.")
      print("    3. Complete OAuth popup -> status transitions to Connected / Active.")

  print("\033[1m\033[92m========================================================================\033[0m\n")


if __name__ == "__main__":
  main()
