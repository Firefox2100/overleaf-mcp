import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


SECRETS_DIR = '/run/secrets' if os.path.isdir('/run/secrets') else None


class Settings(BaseSettings):
    """
    Configurations for the Overleaf MCP bridge.
    """

    model_config = SettingsConfigDict(
        env_prefix='OMCP_',
        env_file_encoding='utf-8',
        **({'secrets_dir': SECRETS_DIR} if SECRETS_DIR else {})
    )

    overleaf_base_url: str = Field(
        default='https://www.overleaf.com',
        description='Base URL for Overleaf API requests.'
    )
    overleaf_email: str = Field(
        ...,
        description='Email for Overleaf API authentication.'
    )
    overleaf_password: str = Field(
        ...,
        description='Password for Overleaf API authentication.'
    )


CONFIG = Settings(_env_file=os.getenv('OMCP_ENV_FILE', '.env'))
