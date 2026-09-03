from pydantic import Field

from .common import CommonBase
from .compile_image import CompileImage


class ProjectConfig(CommonBase):
    """
    Represents a project's compile-relevant configuration. Overleaf CE
    exposes no plain REST endpoint for this — it's only available through
    the real-time API's joinProject response.
    """

    name: str = Field(
        description='Project name.'
    )
    compiler: str = Field(
        description='LaTeX engine used to compile the project, e.g. "pdflatex".'
    )
    root_doc_id: str | None = Field(
        default=None,
        validation_alias='rootDoc_id',
        description='Id of the root document, if set.'
    )
    root_doc_path: str | None = Field(
        default=None,
        description=(
            'Path of the root document, resolved from root_doc_id. If unset, Overleaf '
            'falls back to a doc named "main.tex", or the project\'s only doc if there is '
            'exactly one — otherwise a multi-file project without this set will fail to '
            'compile with "no main file specified".'
        )
    )
    main_bibliography_doc_id: str | None = Field(
        default=None,
        validation_alias='mainBibliographyDoc_id',
        description='Id of the main bibliography document, if set.'
    )
    main_bibliography_doc_path: str | None = Field(
        default=None,
        description='Path of the main bibliography document, resolved from main_bibliography_doc_id.'
    )
    spell_check_language: str | None = Field(
        default=None,
        description='Spell-check dictionary language code. Cosmetic only — has no effect on compilation.'
    )
    image_name: str | None = Field(
        default=None,
        description=(
            'TeX Live image the project is configured to compile with. Only meaningfully '
            'selectable when available_images is non-empty (CEP with sandboxed compiles '
            'enabled) — otherwise this reflects a fixed, unchangeable default.'
        )
    )
    available_images: list[CompileImage] = Field(
        default_factory=list,
        description=(
            'TeX Live images available to select via set_compile_image. Empty on a server '
            'without CEP sandboxed compiles enabled.'
        )
    )
