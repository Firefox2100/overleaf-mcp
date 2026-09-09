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


class FileContent(CommonBase):
    """
    Represents a document's or file's content, read as text, together
    with whether it's a linked file.
    """

    content: str = Field(
        description='The content, or the requested line range for a tool that slices it.'
    )
    type: EntityType = Field(
        description=(
            'Entity kind: "doc" for a live, collaboratively-edited document (always editable '
            'with overwrite_file/patch_file); "file" for a binary upload or a linked file (always '
            'read-only through those tools, regardless of linked_file_data — refresh a linked file '
            'with refresh_linked_file instead).'
        )
    )
    linked_file_data: dict | None = Field(
        default=None,
        description=(
            'Present when this was created from an external source (e.g. a URL import or a '
            'Zotero-synced .bib), refreshable with refresh_linked_file. Shape varies by provider; '
            'always has a "provider" key identifying it (e.g. "zotero", "url"). Never present for '
            'a "doc"; None for a "file" that was uploaded directly rather than linked.'
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
