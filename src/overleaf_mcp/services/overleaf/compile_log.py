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
_LATEX_WARNING = re.compile(r"^LaTeX Warning: (?P<message>[^\r\n]*)", re.MULTILINE)
_PACKAGE_WARNING = re.compile(
    r"^Package (?P<package>\S+) Warning: (?P<message>[^\r\n]*)", re.MULTILINE
)
_INPUT_LINE_SUFFIX = re.compile(r" on input line (?P<line>\d+)\.$")


def _warning_details(message: str) -> tuple[str, int | None]:
    line_match = _INPUT_LINE_SUFFIX.search(message)
    if line_match is None:
        return message.strip(), None
    return message[:line_match.start()].strip(), int(line_match.group("line"))


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
    for match in _LATEX_WARNING.finditer(text):
        message, line = _warning_details(match.group("message"))
        entries.append(CompileLogEntry(level="warning", line=line, message=message))
    for match in _PACKAGE_WARNING.finditer(text):
        message, line = _warning_details(match.group("message"))
        entries.append(
            CompileLogEntry(level="warning", line=line, message=f"[{match.group('package')}] {message}")
        )
    return entries
