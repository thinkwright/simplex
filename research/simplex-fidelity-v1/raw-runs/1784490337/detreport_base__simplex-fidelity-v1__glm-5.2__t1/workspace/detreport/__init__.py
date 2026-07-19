"""detreport: build deterministic category-grouped reports from events.

Public API:
    build_report(events) -> str
    ReportError
"""

from detreport.public import ReportError, build_report

__all__ = ["ReportError", "build_report"]