from pydantic import Field

from .common import CommonBase


class CompileImage(CommonBase):
    """
    Represents a TeX Live image available to compile a project with (CEP
    sandboxed compiles). Always empty on a server without that feature.
    """

    image_name: str = Field(
        description='Image identifier, used as the value for set_compile_image.'
    )
    image_desc: str | None = Field(
        default=None,
        description='Human-readable label for the image.'
    )
    allowed: bool = Field(
        default=True,
        description='Whether the authenticated account is allowed to select this image.'
    )
