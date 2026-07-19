"""detreport public API.

Exposes :func:`build_report` and :class:`ReportError` from
:mod:`detreport.public` so that ``from detreport import build_report,
ReportError`` works in addition to ``from detreport.public import ...``.
"""

from detreport.public import ReportError, build_report

__all__ = ["build_report", "ReportError"]