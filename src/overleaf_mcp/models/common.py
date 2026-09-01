from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CommonBase(BaseModel):
    """
    Base class for common model configuration.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
