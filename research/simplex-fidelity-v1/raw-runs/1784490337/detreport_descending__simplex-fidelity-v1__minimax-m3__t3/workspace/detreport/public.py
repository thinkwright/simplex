"""Public API for detreport.

Exposes :func:`build_report` and :class:`ReportError`.
"""

from __future__ import annotations

from .core import ReportError, build_report

__all__ = ["build_report", "ReportError"]