from typing import Literal

from pydantic import Field

from .common import CommonBase

EntityType = Literal["doc", "file", "folder"]


class FileEntry(CommonBase):
    """
    Represents a single entry in a folder listing.
    """

    name: str = Field(
        description='Entry name.'
    )
    type: EntityType = Field(
        description='Entry kind: a text document, a binary file, or a folder.'
    )
    linked_file_data: dict | None = Field(
        default=None,
        description=(
            'Present when this file was created from an external source (e.g. a URL import '
            'or a Zotero-synced .bib), refreshable with refresh_linked_file. Shape varies by '
            'provider; always has a "provider" key.'
        )
    )


class CreatedEntity(CommonBase):
    """
    Represents the response returned when a doc or folder is created.
    """

    id: str = Field(
        validation_alias='_id',
        description='Id of the newly created entity.'
    )
    name: str = Field(
        description='Name of the newly created entity.'
    )


class UploadedFile(CommonBase):
    """
    Represents the response returned when a file is uploaded.
    """

    success: bool = Field(
        description='Whether the upload succeeded.'
    )
    entity_id: str = Field(
        validation_alias='entity_id',
        description='Id of the created or overwritten file.'
    )
    entity_type: str = Field(
        validation_alias='entity_type',
        description='Entity type of the uploaded file.'
    )
