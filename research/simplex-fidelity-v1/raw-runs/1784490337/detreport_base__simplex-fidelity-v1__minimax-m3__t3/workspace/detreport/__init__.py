"""detreport package.

Exposes build_report and ReportError via detreport.public.
"""

from .public import ReportError, build_report

__all__ = ["build_report", "ReportError"]