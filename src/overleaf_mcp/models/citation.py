from pydantic import Field

from .common import CommonBase


class CitationEntry(CommonBase):
    """
    Represents a single BibTeX entry.
    """

    key: str = Field(
        description='Citation key, e.g. "smith2020".'
    )
    entry_type: str = Field(
        description='BibTeX entry type, e.g. "article" or "book".'
    )
    path: str = Field(
        description='Path of the .bib file this entry is defined in.'
    )
    fields: dict[str, str] = Field(
        default_factory=dict,
        description='All other BibTeX fields, e.g. title, author, year, journal.'
    )


class CitationCheckResult(CommonBase):
    """
    Represents the result of cross-referencing citation usage against
    definitions across a project.
    """

    undefined_keys: list[str] = Field(
        description='Keys used in a \\cite-family command with no matching BibTeX entry.'
    )
    unused_keys: list[str] = Field(
        description='Keys with a BibTeX entry that are never used in a \\cite-family command.'
    )
