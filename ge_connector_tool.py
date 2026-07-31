#!/usr/bin/env python3
"""Gemini Enterprise 3P Connector Automation Tool.

Enterprise CLI tool for provisioning and configuring 3P data connectors
(SharePoint,
OneDrive, Outlook, Teams, Confluence, Jira) for Gemini Enterprise (Discovery
Engine)
on Google Cloud.
"""

import argparse
import json
import os
import sys

# Ensure local packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# pylint: disable=g-import-not-at-top
from core.logger import setup_logger
from core.preflight import PreflightValidator
from core.rollback import RollbackManager
from plugins.sharepoint_federated import SharePointFederatedPlugin
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
      default="sharepoint_federated",
      help="Connector type to provision (default: sharepoint_federated)",
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
      help=(
          "Simulate execution, validate permissions, and render proposed change"
          " plan"
      ),
  )
  parser.add_argument(
      "--interactive",
      action="store_true",
      default=True,
      help=(
          "Run interactive wizard prompts (default: True unless --config is"
          " supplied)"
      ),
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
    logger.error(
        "Pre-flight validation failed. Correct the errors above and re-run."
    )
    sys.exit(1)

  for warning in pf_res.warnings:
    logger.warning("Pre-flight Warning: %s", warning)

  # 2. Instantiate Cloud Service Providers
  entra_provider = EntraProvider(logger=logger, rollback_mgr=rollback_mgr)
  gcp_provider = GcpProvider(logger=logger, rollback_mgr=rollback_mgr)

  # 3. Instantiate Selected Connector Plugin
  sp_plugin = SharePointFederatedPlugin(
      logger=logger,
      entra_provider=entra_provider,
      gcp_provider=gcp_provider,
      rollback_mgr=rollback_mgr,
  )
  plugin_registry = {
      "sharepoint_federated": sp_plugin,
  }

  plugin = plugin_registry.get(args.connector)
  if not plugin:
    logger.error(
        "Unsupported connector type: '%s'. Available: %s",
        args.connector,
        list(plugin_registry.keys()),
    )
    sys.exit(1)

  logger.info("Loaded Plugin: %s (%s)", plugin.name, plugin.connector_type)

  # 4. Gather Configuration Parameters
  defaults = {
      "gcp_project": pf_res.gcp_project,
      "entra_tenant_id": pf_res.entra_tenant_id,
      "is_global_admin": pf_res.is_global_admin,
  }

  if args.config:
    logger.info("Loading configuration file '%s'...", args.config)
    try:
      with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
      config["is_global_admin"] = pf_res.is_global_admin
    except Exception as e:  # pylint: disable=broad-exception-caught
      logger.error("Failed to read config file '%s': %s", args.config, str(e))
      sys.exit(1)
  else:
    # Guided Interactive Wizard
    config = plugin.prompt_config_interactive(defaults)

  # 5. Validate Configuration Parameters
  validation_errors = plugin.validate_config(config)
  if validation_errors:
    for err in validation_errors:
      logger.error("Config Error: %s", err)
    sys.exit(1)

  # 6. Execute Dry-Run or Real Provisioning
  if args.dry_run:
    logger.info("Executing in DRY-RUN mode...")
    plugin.provision(config, dry_run=True)
    logger.info("Dry-run execution completed. No resources were mutated.")
    sys.exit(0)

  try:
    logger.info("Initiating resource provisioning sequence...")
    provision_res = plugin.provision(config, dry_run=False)

    # 7. Post-Flight Diagnostic Verification
    logger.info("Performing post-flight health verification...")
    is_healthy = plugin.verify(config, provision_res)

    # 8. Disable rollback on successful completion
    rollback_mgr.disable()

    # 9. Output Actionable Summary Report
    client_id = provision_res["client_id"]
    datastore_id = provision_res["datastore_id"]
    secret_path = provision_res["secret_path"]
    consent_granted = provision_res["admin_consent_granted"]
    gcp_project = config["gcp_project"]

    report = [
        "\n\033[1m\033[92m========================================================================",
        "                PROVISIONING COMPLETED SUCCESSFULLY!",
        "========================================================================\033[0m",
        f"\033[1mGCP Project:\033[0m          {gcp_project}",
        f"\033[1mData Store ID:\033[0m        {datastore_id}",
        f"\033[1mEntra Client ID:\033[0m      {client_id}",
        f"\033[1mSecret Manager Path:\033[0m  {secret_path}",
        (
            "\033[1mHealth Polling Status:\033[0m"
            f" {'ACTIVE' if is_healthy else 'PROVISIONING_IN_PROGRESS'}"
        ),
        "------------------------------------------------------------------------",
    ]

    if not consent_granted:
      report.extend([
          (
              "\033[1m\033[93m[ACTION REQUIRED] ADMIN CONSENT NEEDED (Microsoft"
              " Entra Admin Center):\033[0m"
          ),
          (
              "Automated background consent was skipped (user is not Global"
              " Admin)."
          ),
          (
              "An admin can grant consent directly in Microsoft Entra Admin"
              " Center with zero redirect pages:"
          ),
          (
              "  1. Open Portal:"
              " https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/"
              f"{client_id}"
          ),
          "  2. Click 'Grant admin consent for <Tenant>'",
          (
              "  3. Green checkmarks will appear next to Sites.Search.All,"
              " Sites.Read.All, and User.Read."
          ),
          "------------------------------------------------------------------------",
      ])

    report.extend([
        "\033[1mNext Steps for Administrators:\033[0m",
        (
            "1. View Data Store in Console:"
            f" https://console.cloud.google.com/gemini-enterprise/data-stores?project={gcp_project}"
        ),
        (
            "2. Instruct end users that their first SharePoint search will"
            " request a one-time OAuth 'Authorize' consent."
        ),
        "\033[1m\033[92m========================================================================\033[0m",
    ])

    print("\n".join(report))

  except Exception as e:  # pylint: disable=broad-exception-caught
    logger.critical("Provisioning sequence aborted due to error: %s", str(e))
    rollback_mgr.execute_rollback()
    sys.exit(1)


if __name__ == "__main__":
  main()
