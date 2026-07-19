"""Public API for the detreport package.

Exposes :func:`build_report` and :class:`ReportError`.
"""

from detreport.core import build_report, ReportError

__all__ = ["build_report", "ReportError"]