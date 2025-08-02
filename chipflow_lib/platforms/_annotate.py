import json
from types import MethodType
import pydantic
from amaranth.lib import meta

from typing import (
    Any, Annotated, NamedTuple, Self, TypeVar
)
from typing_extensions import TypedDict, is_typeddict

_T_TypedDict = TypeVar('_T_TypedDict')
def amaranth_annotate(modeltype: type[_T_TypedDict], schema_id: str, member: str = '__chipflow_annotation__', decorate_object = False):
    # a bit of nastyness as can't set TypedDict as a bound yet
    if not is_typeddict(modeltype):
        raise TypeError(f"amaranth_annotate must be passed a TypedDict, not {modeltype}")

    # interesting pydantic issue gets hit if arbitrary_types_allowed is False
    if hasattr(modeltype, '__pydantic_config__'):
        config: pydantic.ConfigDict = getattr(modeltype, '__pydantic_config__')
        config['arbitrary_types_allowed'] = True
    else:
        config = pydantic.ConfigDict()
        config['arbitrary_types_allowed'] = True
        setattr(modeltype, '__pydantic_config__', config)

    PydanticModel = pydantic.TypeAdapter(modeltype)

    def annotation_schema():
        schema = PydanticModel.json_schema()
        schema['$schema'] = "https://json-schema.org/draft/2020-12/schema"
        schema['$id'] = schema_id
        return schema

    class Annotation(meta.Annotation):
        "Generated annotation class"
        schema = annotation_schema()

        def __init__(self, parent):
            self.parent = parent

        @property
        def origin(self):  # type: ignore
            return self.parent

        def as_json(self):  # type: ignore
            # TODO: this is slow, but atm necessary as dump_python doesn't do the appropriate
            # transformation of things like PosixPath. Figure out why, maybe log issue/PR with
            # pydantic
            # return json.loads(PydanticModel.dump_json(getattr(self.parent, member)))
            return PydanticModel.dump_python(getattr(self.parent, member), mode='json')

    def decorate_class(klass):
        if hasattr(klass, 'annotations'):
            old_annotations = klass.annotations
        else:
            old_annotations = None
        def annotations(self, obj, /):  # type: ignore
            if old_annotations:
                annotations = old_annotations(self, obj)  # type: ignore
            else:
                annotations = super(klass, obj).annotations(obj)
            annotation = Annotation(self)
            return annotations + (annotation,)  # type: ignore


        klass.annotations = annotations
        return klass

    def decorate_obj(obj):
        old_annotations = obj.annotations
        def annotations(self, origin , /):  # type: ignore
            print(f"annotation obj {obj}")
            annotations = old_annotations(origin)  # type: ignore
            annotation = Annotation(self)
            print(f"  returning {[a.as_json() for a in (annotations + (annotation,))]}")
            return annotations + (annotation,)  # type: ignore

        setattr(obj, 'annotations',  MethodType(annotations, obj))

        # if hasattr(obj, 'annotations'):
        #     old_annotations = obj.annotations
        # else:
        #     old_annotations = None

        # def annotations(self, origin):
        #     print("annotations ({self},{origin})")
        #     if old_annotations:
        #         annotations = old_annotations(origin)
        #     else:
        #         annotations = super(obj.__class__, obj).annotations(obj)
        #     annotation = Annotation(self)
        #     print("  returning {[a.to_json() for a in (annotations + (annotation,))}")
        #     return annotations + (annotation,)

        return obj

    if decorate_object:
        return decorate_obj
    else:
        return decorate_class


