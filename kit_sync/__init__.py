"""Renders canonical agents, skills and instructions into Copilot and Claude Code layouts."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentic-sdlc-kit")
except PackageNotFoundError:  # running from a source checkout without install
    __version__ = "0.0.0"
