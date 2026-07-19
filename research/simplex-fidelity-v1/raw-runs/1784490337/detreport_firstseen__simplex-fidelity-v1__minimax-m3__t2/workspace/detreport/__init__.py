"""detreport: deterministic event report builder.

Public API is exposed via :mod:`detreport.public`.
"""

from detreport.public import build_report, ReportError

__all__ = ["build_report", "ReportError"]