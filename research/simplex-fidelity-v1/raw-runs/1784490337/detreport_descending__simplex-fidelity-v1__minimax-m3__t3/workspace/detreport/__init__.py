"""detreport package.

Builds a deterministic JSON report from a list of events.
Only the Python standard library is used.
"""

from __future__ import annotations

from .core import ReportError, build_report

__all__ = ["build_report", "ReportError"]