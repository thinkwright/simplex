"""Public API for detreport.

Exposes build_report and ReportError.
"""

from ._core import ReportError, build_report

__all__ = ["build_report", "ReportError"]