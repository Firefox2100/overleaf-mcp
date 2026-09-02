from pydantic import Field

from .common import CommonBase


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
