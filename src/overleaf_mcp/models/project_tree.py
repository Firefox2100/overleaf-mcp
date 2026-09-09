from __future__ import annotations

from pydantic import Field

from .common import CommonBase
from .entity import EntityType


class PathResolutionError(Exception):
    """Raised when a path doesn't resolve against a project's folder tree."""


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
    linked_file_data: dict | None = Field(
        default=None,
        description=(
            'Present on a file created from an external source (e.g. a URL import or a '
            'Zotero-synced .bib). Shape varies by provider; always has a "provider" key.'
        )
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


def path_segments(path: str) -> list[str]:
    return [segment for segment in path.strip("/").split("/") if segment]


def flatten_docs(folder: TreeFolder, prefix: str = "") -> list[tuple[str, str]]:
    """
    Return (path, doc_id) for every doc in the tree, depth-first.
    """
    docs = [(f"{prefix}/{doc.name}" if prefix else doc.name, doc.id) for doc in folder.docs]
    for child in folder.folders:
        child_prefix = f"{prefix}/{child.name}" if prefix else child.name
        docs += flatten_docs(child, child_prefix)
    return docs


def find_doc_path(folder: TreeFolder, doc_id: str) -> str | None:
    return next((path for path, id_ in flatten_docs(folder) if id_ == doc_id), None)


def flatten_entities(folder: TreeFolder, prefix: str = "") -> list[tuple[str, EntityType, str]]:
    """
    Return (path, entity_type, entity_id) for every doc and file in the
    tree, depth-first. entity_type is "doc" or "file" — unlike
    flatten_docs, this also includes file_refs (binary uploads and linked
    files, e.g. a Zotero-synced .bib), which is what content-scanning
    operations (search, citations) need to see them.
    """
    entities: list[tuple[str, EntityType, str]] = (
        [(f"{prefix}/{doc.name}" if prefix else doc.name, "doc", doc.id) for doc in folder.docs]
        + [(f"{prefix}/{f.name}" if prefix else f.name, "file", f.id) for f in folder.file_refs]
    )
    for child in folder.folders:
        child_prefix = f"{prefix}/{child.name}" if prefix else child.name
        entities += flatten_entities(child, child_prefix)
    return entities


def resolve_folder(root: TreeFolder, path: str) -> TreeFolder:
    folder = root
    for segment in path_segments(path):
        match = next((f for f in folder.folders if f.name == segment), None)
        if match is None:
            raise PathResolutionError(f"No such folder: {path!r}")
        folder = match
    return folder


def resolve_entity_ref(root: TreeFolder, path: str) -> tuple[EntityType, TreeEntity | TreeFolder]:
    """
    Resolve a path to its entity, keeping the full tree object rather than
    just its id — needed to read a "file" entity's linked_file_data.
    """
    segments = path_segments(path)
    if not segments:
        raise PathResolutionError("Path must not be empty")
    folder = resolve_folder(root, "/".join(segments[:-1]))
    name = segments[-1]
    for child in folder.folders:
        if child.name == name:
            return "folder", child
    for child in folder.docs:
        if child.name == name:
            return "doc", child
    for child in folder.file_refs:
        if child.name == name:
            return "file", child
    raise PathResolutionError(f"No such path: {path!r}")


def resolve_entity(root: TreeFolder, path: str) -> tuple[EntityType, str]:
    entity_type, entity = resolve_entity_ref(root, path)
    return entity_type, entity.id
