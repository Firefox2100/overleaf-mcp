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


class DownloadedFile(CommonBase):
    """
    Represents a file saved to local disk.
    """

    path: str = Field(
        description='Local filesystem path the file was saved to.'
    )
    size_bytes: int = Field(
        description='Size of the saved file in bytes.'
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
