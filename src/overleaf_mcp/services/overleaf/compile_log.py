"""
Lightweight parser for Overleaf/CLSI compile logs.

There is no structured errors endpoint (verified against the Overleaf
source) — the web app parses the raw log client-side in the browser. This
covers the common cases: file:line errors (emitted when the compile
request is made with the `-file-line-error` flag) and LaTeX/package
warnings. It is not a full port of Overleaf's own log parser.
"""

import re

from overleaf_mcp.models.compile import CompileLogEntry

_FILE_LINE_ERROR = re.compile(r"^(?P<file>.+?):(?P<line>\d+): (?P<message>.+)$", re.MULTILINE)
_LATEX_WARNING = re.compile(r"^LaTeX Warning: (?P<message>.+?)(?: on input line (?P<line>\d+)\.)?$", re.MULTILINE)
_PACKAGE_WARNING = re.compile(
    r"^Package (?P<package>\S+) Warning: (?P<message>.+?)(?: on input line (?P<line>\d+)\.)?$", re.MULTILINE
)


def parse_compile_log(text: str) -> list[CompileLogEntry]:
    entries = [
        CompileLogEntry(
            level="error",
            file=match.group("file"),
            line=int(match.group("line")),
            message=match.group("message").strip(),
        )
        for match in _FILE_LINE_ERROR.finditer(text)
    ]
    entries += [
        CompileLogEntry(
            level="warning",
            line=int(match.group("line")) if match.group("line") else None,
            message=match.group("message").strip(),
        )
        for match in _LATEX_WARNING.finditer(text)
    ]
    entries += [
        CompileLogEntry(
            level="warning",
            line=int(match.group("line")) if match.group("line") else None,
            message=f"[{match.group('package')}] {match.group('message').strip()}",
        )
        for match in _PACKAGE_WARNING.finditer(text)
    ]
    return entries
