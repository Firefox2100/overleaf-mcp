from pydantic import Field

from .common import CommonBase


class Collaborator(CommonBase):
    """
    Represents a project collaborator (not including the owner).
    """

    id: str = Field(
        validation_alias='_id',
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
    privileges: str = Field(
        description='Access level, e.g. "readAndWrite", "readOnly", or "review".'
    )
