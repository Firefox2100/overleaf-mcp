from __future__ import annotations

from pydantic import Field

from .common import CommonBase


class TreeEntity(CommonBase):
    """
    Represents a doc or file leaf in a project's live folder tree.
    """

    id: str = Field(
        validation_alias='_id',
        description='Entity id.'
    )
    name: str = Field(
        description='Entity name.'
    )


class TreeFolder(CommonBase):
    """
    Represents a folder in a project's live folder tree, as returned by
    joining the project over the real-time API.
    """

    id: str = Field(
        validation_alias='_id',
        description='Folder id.'
    )
    name: str = Field(
        description='Folder name.'
    )
    folders: list[TreeFolder] = Field(
        default_factory=list,
        description='Child folders.'
    )
    docs: list[TreeEntity] = Field(
        default_factory=list,
        description='Child text documents.'
    )
    file_refs: list[TreeEntity] = Field(
        default_factory=list,
        validation_alias='fileRefs',
        description='Child binary files.'
    )
