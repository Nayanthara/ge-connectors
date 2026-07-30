"""Rollback Manager Module for Gemini Enterprise Connector Tool.

Provides stack-based resource mutation tracking and signal-trapped cleanup
handlers
to roll back transient resources if execution is aborted or fails midway.
"""

import logging
import signal
import sys
import typing


class RollbackAction(typing.NamedTuple):
  """Encapsulates a single undo/cleanup operation."""

  description: str
  action_fn: typing.Callable[[], None]


class RollbackManager:
  """Manages an execution stack of rollback actions."""

  def __init__(self, logger: logging.Logger):
    self.logger = logger
    self._stack: typing.List[RollbackAction] = []
    self._enabled: bool = True
    self._register_signal_handlers()

  def _register_signal_handlers(self) -> None:
    """Register signal handlers for SIGINT (Ctrl+C) and SIGTERM."""
    signal.signal(signal.SIGINT, self._handle_signal)
    signal.signal(signal.SIGTERM, self._handle_signal)

  def _handle_signal(self, signum: int, unused_frame: typing.Any) -> None:
    """Signal handler callback for clean execution abort."""
    sig_name = signal.Signals(signum).name
    self.logger.warning(
        "Received signal %s (%d). Initiating automated rollback...",
        sig_name,
        signum,
    )
    self.execute_rollback()
    sys.exit(128 + signum)

  def register(
      self, description: str, action_fn: typing.Callable[[], None]
  ) -> None:
    """Register a cleanup action onto the top of the rollback stack.

    Args:
        description: Description of what will be cleaned up.
        action_fn: Callable containing the cleanup logic.
    """
    if not self._enabled:
      return
    self.logger.debug("Registered rollback action: %s", description)
    self._stack.append(
        RollbackAction(description=description, action_fn=action_fn)
    )

  def pop_last(self) -> None:
    """Remove the most recent rollback action."""
    if self._stack:
      removed = self._stack.pop()
      self.logger.debug("Cleared rollback action: %s", removed.description)

  def disable(self) -> None:
    """Disable rollback execution upon successful completion."""
    self._enabled = False
    self._stack.clear()
    self.logger.debug("Rollback stack disabled after successful completion.")

  def execute_rollback(self) -> None:
    """Execute all registered cleanup actions in LIFO order."""
    if not self._stack:
      self.logger.info("No transient resources to roll back.")
      return

    self.logger.warning(
        "Executing rollback for %d registered operations...",
        len(self._stack),
    )
    while self._stack:
      item = self._stack.pop()
      self.logger.info("Rolling back: %s", item.description)
      try:
        item.action_fn()
        self.logger.info("Successfully rolled back: %s", item.description)
      except Exception as e:  # pylint: disable=broad-exception-caught
        self.logger.error(
            "Failed to roll back '%s': %s", item.description, str(e)
        )

    self.logger.info("Automated rollback sequence completed.")
