from __future__ import annotations

from pydantic import Field

from .common import CommonBase


class SearchMatch(CommonBase):
    """
    Represents a single line matching a search query.
    """

    path: str = Field(
        description='Path of the document containing the match.'
    )
    line: int = Field(
        description='1-indexed line number of the match.'
    )
    text: str = Field(
        description="The full text of the matching line."
    )


class OutlineEntry(CommonBase):
    """
    Represents a single sectioning-command entry in a document's outline.
    """

    level: str = Field(
        description='Sectioning command name, e.g. "section" or "subsection".'
    )
    title: str = Field(
        description='Section title text.'
    )
    line: int = Field(
        description='1-indexed line number the sectioning command appears on.'
    )
    children: list[OutlineEntry] = Field(
        default_factory=list,
        description='Nested subsections.'
    )
