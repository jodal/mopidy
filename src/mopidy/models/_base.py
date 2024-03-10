from typing import Any, Self

import msgspec


class BaseModel(
    msgspec.Struct,
    frozen=True,
    omit_defaults=True,
    repr_omit_defaults=True,
    tag_field="__model__",
    tag=True,
):
    """Base class for all models."""

    def replace(self, **kwargs: Any) -> Self:
        """Return a new instance with updated fields."""
        current_fields = msgspec.structs.asdict(self)
        updated_fields = {**current_fields, **kwargs}
        return type(self)(**updated_fields)

    def serialize(self) -> dict[str, Any]:
        """Serialize the model to a dict."""
        return msgspec.to_builtins(self)
