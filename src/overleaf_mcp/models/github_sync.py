from pydantic import Field

from .common import CommonBase


class GitHubSyncState(CommonBase):
    """
    Represents a project's GitHub-sync link state. Linking/unlinking a
    project isn't supported by this bridge — only syncing an already-
    linked one.
    """

    merge_status: str = Field(
        description=(
            'Sync state: "need-export" (not linked — trigger_sync will fail), "clean", '
            '"diverged", "conflict", or "need-permission".'
        )
    )
    repo_full_name: str | None = Field(
        default=None,
        description='Linked GitHub repo, e.g. "owner/repo". Set only when linked.'
    )
    unmerged_branch_name: str | None = Field(
        default=None,
        description='Branch holding unmerged changes, if any.'
    )
    owner_email: str | None = Field(
        default=None,
        description='Email of the project owner.'
    )
