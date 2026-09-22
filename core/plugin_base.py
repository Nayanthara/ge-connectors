"""Abstract Base Connector Plugin Module for Gemini Enterprise Connector Tool.

Defines the contract and lifecycle interface that all 3P connector plugins
must implement.
"""

import abc
import logging
import typing


class BaseConnectorPlugin(abc.ABC):
  """Abstract Base Class for connector provisioning plugins."""

  def __init__(
      self,
      logger: logging.Logger,
      entra_provider: typing.Any,
      gcp_provider: typing.Any,
      rollback_mgr: typing.Any,
  ):
    self.logger = logger
    self.entra_provider = entra_provider
    self.gcp_provider = gcp_provider
    self.rollback_mgr = rollback_mgr

  @property
  @abc.abstractmethod
  def name(self) -> str:
    """Return the human-readable display name of the connector plugin."""

  @property
  @abc.abstractmethod
  def connector_type(self) -> str:
    """Return the unique technical identifier for the connector plugin."""

  @abc.abstractmethod
  def prompt_config_interactive(
      self, defaults: typing.Dict[str, typing.Any]
  ) -> typing.Dict[str, typing.Any]:
    """Interactively prompt the user for configuration values.

    Args:
        defaults: Pre-populated default values.

    Returns:
        Dictionary containing gathered and validated configuration options.
    """

  @abc.abstractmethod
  def validate_config(
      self, config: typing.Dict[str, typing.Any]
  ) -> typing.List[str]:
    """Validate configuration parameters non-destructively.

    Args:
        config: Configuration dictionary to validate.

    Returns:
        List of error messages (empty list if valid).
    """

  @abc.abstractmethod
  def execute_dry_run(self, config: typing.Dict[str, typing.Any]) -> str:
    """Generate a dry-run plan summary showing proposed mutations.

    Args:
        config: Validated configuration dictionary.

    Returns:
        Formatted multi-line text plan describing actions to be taken.
    """

  @abc.abstractmethod
  def provision(
      self, config: typing.Dict[str, typing.Any], dry_run: bool = False
  ) -> typing.Dict[str, typing.Any]:
    """Execute the end-to-end resource provisioning sequence.

    Args:
        config: Validated configuration dictionary.
        dry_run: If True, simulates actions without making changes.

    Returns:
        Dictionary containing created resource metadata.
    """

  @abc.abstractmethod
  def verify(
      self,
      config: typing.Dict[str, typing.Any],
      provision_result: typing.Dict[str, typing.Any],
  ) -> bool:
    """Perform post-flight health verification on created resources.

    Args:
        config: Configuration dictionary.
        provision_result: Result dictionary returned by provision().

    Returns:
        True if all post-flight health checks pass, False otherwise.
    """

  @abc.abstractmethod
  def generate_terraform(
      self,
      config: typing.Dict[str, typing.Any],
      output_dir: str,
  ) -> typing.List[str]:
    """Generate Terraform configuration files in the specified output directory.

    Args:
        config: Validated configuration dictionary.
        output_dir: Target directory path to write generated .tf files.

    Returns:
        List of generated file paths.
    """

