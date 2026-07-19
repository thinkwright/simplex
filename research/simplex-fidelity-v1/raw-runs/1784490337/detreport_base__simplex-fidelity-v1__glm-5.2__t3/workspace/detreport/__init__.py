"""detreport package: build deterministic integer-cent reports from events.

Only the Python standard library is used.
"""

from detreport.public import ReportError, build_report

__all__ = ["build_report", "ReportError"]