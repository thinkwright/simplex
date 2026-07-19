"""detreport: deterministic event reports in integer cents.

The public API exposes :func:`build_report` and :class:`ReportError`, both
imported from :mod:`detreport.public`.
"""

from detreport.public import ReportError, build_report

__all__ = ["ReportError", "build_report"]