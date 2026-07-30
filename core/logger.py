"""Logging Utility Module for Gemini Enterprise Connector Tool.

Provides a custom logging Formatter that automatically redacts sensitive
information
such as OAuth Bearer tokens, Client Secrets, and API Authorization headers from
all
log output (both stdout and file logs).
"""

import logging
import re
import sys
from typing import List, Optional


class RedactingFormatter(logging.Formatter):
  """Logging Formatter that redacts sensitive strings using regex."""

  def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
    super().__init__(fmt=fmt, datefmt=datefmt)
    # Regex patterns for matching sensitive strings
    self._patterns: List[re.Pattern[str]] = [
        re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
        re.compile(r"(\"password\":\s*\")[^\"]+(\")", re.IGNORECASE),
        re.compile(r"(\"client_secret\":\s*\")[^\"]+(\")", re.IGNORECASE),
        re.compile(r"(client_secret=)[^\s&]+", re.IGNORECASE),
        re.compile(r"(access_token=)[^\s&]+", re.IGNORECASE),
        re.compile(r"(Authorization:\s*)[^\s]+", re.IGNORECASE),
    ]

  def format(self, record: logging.LogRecord) -> str:
    """Format the log record and sanitize sensitive data."""
    formatted = super().format(record)
    for pattern in self._patterns:
      formatted = pattern.sub(
          r"\1[REDACTED]\2" if r"\2" in pattern.pattern else r"\1[REDACTED]",
          formatted,
      )
    return formatted


class ColoredConsoleHandler(logging.StreamHandler):
  """StreamHandler providing ANSI color-coded console logs."""

  # ANSI escape sequences for log levels
  COLORS = {
      logging.DEBUG: "\033[90m",  # Dark Gray
      logging.INFO: "\033[96m",  # Cyan
      logging.WARNING: "\033[93m",  # Yellow
      logging.ERROR: "\033[91m",  # Red
      logging.CRITICAL: "\033[95m",  # Magenta
  }
  RESET = "\033[0m"
  BOLD = "\033[1m"

  def emit(self, record: logging.LogRecord) -> None:
    """Write formatted log message with ANSI color tags."""
    try:
      msg = self.format(record)
      color = self.COLORS.get(record.levelno, self.RESET)
      level_tag = f"{color}{self.BOLD}[{record.levelname}]{self.RESET}"
      sys.stdout.write(f"{level_tag} {msg}\n")
      sys.stdout.flush()
    except (OSError, ValueError, TypeError):
      self.handleError(record)


def setup_logger(
    log_file_path: str = "ge_connector_setup.log", verbose: bool = False
) -> logging.Logger:
  """Initialize and configure the enterprise redacting logger.

  Args:
      log_file_path: Path to the audit log file on disk.
      verbose: Enables DEBUG log level if True, else INFO level.

  Returns:
      Configured Logger instance.
  """
  logger = logging.getLogger("ge_connector_tool")
  logger.setLevel(logging.DEBUG if verbose else logging.INFO)
  logger.handlers.clear()

  # Formatter for file audit log
  file_formatter = RedactingFormatter(
      fmt="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
      datefmt="%Y-%m-%d %H:%M:%S",
  )

  # File Handler
  file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(file_formatter)
  logger.addHandler(file_handler)

  # Console Handler (Colorized)
  console_formatter = RedactingFormatter(fmt="%(message)s")
  console_handler = ColoredConsoleHandler()
  console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
  console_handler.setFormatter(console_formatter)
  logger.addHandler(console_handler)

  return logger
