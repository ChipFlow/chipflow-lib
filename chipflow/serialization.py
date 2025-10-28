# SPDX-License-Identifier: BSD-2-Clause

from dataclasses import dataclass

from pydantic import BaseModel, PlainSerializer, model_serializer

@dataclass
class OmitIfNone:
    """Marker for fields that should be omitted from serialization when None."""
    pass

class SelectiveSerializationModel(BaseModel):
    """
    Base model that supports selective field serialization.

    Fields annotated with OmitIfNone() will be excluded from serialized
    output when their value is None. This provides cleaner JSON output
    for optional configuration fields.
    """
    @model_serializer
    def _serialize(self):
        skip_if_none = set()
        serialize_aliases = dict()

        # Gather fields that should omit if None
        for name, field_info in self.model_fields.items():
            if any(
                isinstance(metadata, OmitIfNone) for metadata in field_info.metadata
            ):
                skip_if_none.add(name)
            elif field_info.serialization_alias:
                serialize_aliases[name] = field_info.serialization_alias

        serialized = dict()

        for name, value in self:
            # Skip serializing None if it was marked with "OmitIfNone"
            if value is None and name in skip_if_none:
                continue
            serialize_key = serialize_aliases.get(name, name)

            # Run Annotated PlainSerializer
            for metadata in self.model_fields[name].metadata:
                if isinstance(metadata, PlainSerializer):
                    value = metadata.func(value)  # type: ignore

            serialized[serialize_key] = value

        return serialized
