from typing import Literal

from pydantic import Field

from .common import CommonBase


class TrackedChange(CommonBase):
    """
    Represents a single tracked change (CEP review mode) in a document.
    """

    id: str = Field(
        description='Tracked-change id, used to accept it.'
    )
    path: str = Field(
        description='Path of the document the change is in.'
    )
    type: Literal["insert", "delete"] = Field(
        description='Whether text was inserted or deleted.'
    )
    text: str = Field(
        description='The inserted or deleted text.'
    )
    position: int = Field(
        description='Character position the change starts at.'
    )
    user_id: str = Field(
        description='Id of the user who made the change.'
    )
    timestamp: str = Field(
        description='When the change was made, ISO 8601.'
    )
