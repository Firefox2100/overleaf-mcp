from pydantic import AliasPath, Field

from .common import CommonBase


class HistoryUser(CommonBase):
    """
    Represents a user attributed to a history update or diff chunk.
    """

    id: str = Field(
        description='User id.'
    )
    email: str = Field(
        description='User email.'
    )
    first_name: str | None = Field(
        default=None,
        description='User first name.'
    )
    last_name: str | None = Field(
        default=None,
        description='User last name.'
    )


class HistoryUpdate(CommonBase):
    """
    Represents one entry in a project's change history.
    """

    from_v: int = Field(
        description='Version the update starts from.'
    )
    to_v: int = Field(
        description='Version the update ends at.'
    )
    users: list[HistoryUser] = Field(
        default_factory=list,
        validation_alias=AliasPath('meta', 'users'),
        description='Users who made this update.'
    )
    start_ts: int = Field(
        validation_alias=AliasPath('meta', 'start_ts'),
        description='Update start time, ms since epoch.'
    )
    end_ts: int = Field(
        validation_alias=AliasPath('meta', 'end_ts'),
        description='Update end time, ms since epoch.'
    )
    pathnames: list[str] = Field(
        default_factory=list,
        description='Paths whose content changed in this update.'
    )
    project_ops: list[dict] = Field(
        default_factory=list,
        validation_alias='project_ops',
        description='File-level operations (add/remove/rename) in this update, in Overleaf\'s own raw shape.'
    )


class HistoryPage(CommonBase):
    """
    Represents one page of a project's change history.
    """

    updates: list[HistoryUpdate] = Field(
        description='Updates on this page, most recent first.'
    )
    next_before_timestamp: int | None = Field(
        default=None,
        description='Pass as `before` to fetch the next (older) page. None if there is no more history.'
    )


class DiffChunk(CommonBase):
    """
    Represents one chunk of a diff between two versions of a document.
    Exactly one of unchanged/inserted/deleted is set.
    """

    unchanged: str | None = Field(
        default=None,
        validation_alias='u',
        description='Text unchanged between the two versions.'
    )
    inserted: str | None = Field(
        default=None,
        validation_alias='i',
        description='Text inserted since the earlier version.'
    )
    deleted: str | None = Field(
        default=None,
        validation_alias='d',
        description='Text deleted since the earlier version.'
    )
    users: list[HistoryUser] = Field(
        default_factory=list,
        validation_alias=AliasPath('meta', 'users'),
        description='Users attributed to this chunk, for inserted/deleted chunks.'
    )


class RestoredEntity(CommonBase):
    """
    Represents the response returned when a file is restored from history.
    """

    id: str = Field(
        description='Id of the newly created entity holding the restored content.'
    )
    type: str = Field(
        description='Entity type of the restored content, e.g. "doc".'
    )


class HistoryLabel(CommonBase):
    """
    Represents a named checkpoint ("label") on a specific history version.
    """

    id: str = Field(
        description='Label id.'
    )
    comment: str = Field(
        description='Label text.'
    )
    version: int = Field(
        description='Version this label marks.'
    )
    user_display_name: str | None = Field(
        default=None,
        validation_alias='user_display_name',
        description='Name of the user who created the label.'
    )
    created_at: str = Field(
        validation_alias='created_at',
        description='When the label was created, ISO 8601.'
    )
