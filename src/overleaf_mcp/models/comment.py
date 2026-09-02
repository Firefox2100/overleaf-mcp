from pydantic import Field

from .common import CommonBase


class CommentAuthor(CommonBase):
    """
    Represents a comment thread's message author or resolver.
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


class CommentMessage(CommonBase):
    """
    Represents a single message in a comment thread.
    """

    id: str = Field(
        description='Message id.'
    )
    content: str = Field(
        description='Message text.'
    )
    timestamp: int = Field(
        description='When the message was posted, ms since epoch.'
    )
    user_id: str = Field(
        validation_alias='user_id',
        description='Id of the user who posted the message.'
    )
    user: CommentAuthor | None = Field(
        default=None,
        description='User who posted the message.'
    )


class CommentThread(CommonBase):
    """
    Represents a comment thread: its anchor location (if still anchored to
    text in a doc) and its messages.
    """

    id: str = Field(
        description='Thread id.'
    )
    path: str | None = Field(
        default=None,
        description='Path of the document the thread is anchored in, if still anchored.'
    )
    anchor_text: str | None = Field(
        default=None,
        description='The commented-on text, if the thread is still anchored.'
    )
    resolved: bool = Field(
        default=False,
        description='Whether the thread is resolved.'
    )
    resolved_by: CommentAuthor | None = Field(
        default=None,
        validation_alias='resolved_by_user',
        description='User who resolved the thread, if resolved.'
    )
    messages: list[CommentMessage] = Field(
        default_factory=list,
        description='Messages in the thread, oldest first.'
    )
