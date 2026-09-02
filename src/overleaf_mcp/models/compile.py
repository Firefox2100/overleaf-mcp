from typing import Literal

from pydantic import Field

from .common import CommonBase


class CompileOutputFile(CommonBase):
    """
    Represents a single artifact produced by a compile.
    """

    path: str = Field(
        description='Artifact filename, e.g. "output.pdf" or "output.log".'
    )
    type: str = Field(
        description='Artifact type, e.g. "pdf" or "log".'
    )
    build: str = Field(
        description='Build id this artifact belongs to, used to fetch it afterwards.'
    )


class CompileResult(CommonBase):
    """
    Represents the response returned when a compile is triggered.
    """

    status: str = Field(
        description='Compile outcome, e.g. "success", "failure", or "timedout".'
    )
    output_files: list[CompileOutputFile] = Field(
        default_factory=list,
        description='Artifacts produced by the compile.'
    )
    compile_group: str | None = Field(
        default=None,
        description='Overleaf compile tier used for this compile.'
    )
    clsi_server_id: str | None = Field(
        default=None,
        description='Id of the compile backend that ran this compile, needed to fetch artifacts in a multi-node deployment.'
    )


class WordCount(CommonBase):
    """
    Represents a document or project's word/character counts, from CLSI's
    texcount.
    """

    encode: str = Field(
        description='Text encoding texcount detected.'
    )
    text_words: int = Field(
        description='Word count in the main body text.'
    )
    head_words: int = Field(
        description='Word count in headers (titles, section headings).'
    )
    outside: int = Field(
        description='Word count outside the document environment.'
    )
    headers: int = Field(
        description='Number of headers (sections, subsections, etc.).'
    )
    elements: int = Field(
        description='Number of floating elements (figures, tables, etc.).'
    )
    math_inline: int = Field(
        description='Number of inline math expressions.'
    )
    math_display: int = Field(
        description='Number of displayed (block) math expressions.'
    )
    errors: int = Field(
        description='Number of errors texcount encountered.'
    )
    messages: str = Field(
        description='texcount warning/error messages, if any.'
    )


class CompileLogEntry(CommonBase):
    """
    Represents a single parsed entry from a compile log.
    """

    level: Literal["error", "warning"] = Field(
        description='Severity of the entry.'
    )
    file: str | None = Field(
        default=None,
        description='Source file the entry refers to, when known.'
    )
    line: int | None = Field(
        default=None,
        description='Line number the entry refers to, when known.'
    )
    message: str = Field(
        description='The entry text.'
    )
