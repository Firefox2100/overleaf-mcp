from datetime import datetime

from pydantic import Field

from .common import CommonBase


class ProjectUser(CommonBase):
    """
    Represents a user referenced by a project (owner or last editor).
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


class Project(CommonBase):
    """
    Represents a project as returned by the project listing API.
    """

    id: str = Field(
        description='Project id.'
    )
    name: str = Field(
        description='Project name.'
    )
    archived: bool = Field(
        description='Whether the project is archived.'
    )
    trashed: bool = Field(
        description='Whether the project is trashed.'
    )
    access_level: str = Field(
        description="Caller's access level on the project."
    )
    source: str = Field(
        description='How access to the project was granted.'
    )
    last_updated: datetime = Field(
        description='Timestamp the project was last updated at.'
    )
    last_updated_by: ProjectUser | None = Field(
        default=None,
        description='User who last updated the project.'
    )
    owner: ProjectUser | None = Field(
        default=None,
        description='Project owner.'
    )


class ProjectList(CommonBase):
    """
    Represents a page of the project listing API's response.
    """

    total_size: int = Field(
        description='Total number of projects matching the query.'
    )
    projects: list[Project] = Field(
        description='Matching projects.'
    )


class CreatedProjectOwner(CommonBase):
    """
    Represents the owner referenced in a project creation response.
    """

    id: str = Field(
        validation_alias='_id',
        description='Owner user id.'
    )
    email: str = Field(
        description='Owner email.'
    )
    first_name: str | None = Field(
        default=None,
        validation_alias='first_name',
        description='Owner first name.'
    )
    last_name: str | None = Field(
        default=None,
        validation_alias='last_name',
        description='Owner last name.'
    )


class CreatedProject(CommonBase):
    """
    Represents the response returned when a project is created.
    """

    project_id: str = Field(
        validation_alias='project_id',
        description='Id of the newly created project.'
    )
    owner_ref: str = Field(
        validation_alias='owner_ref',
        description='Id of the project owner.'
    )
    owner: CreatedProjectOwner = Field(
        description='Project owner.'
    )
