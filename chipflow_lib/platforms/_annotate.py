from types import MethodType
import pydantic
from amaranth.lib import meta
from typing import Any, Annotated, NamedTuple, Self, TypeVar
from typing_extensions import TypedDict, is_typeddict
_T_TypedDict = TypeVar('_T_TypedDict')

def amaranth_annotate(modeltype: type['_T_TypedDict'], schema_id: str, member='__chipflow_annotation__', decorate_object = False):
    if not is_typeddict(modeltype):
        raise TypeError(f'''amaranth_annotate must be passed a TypedDict, not {modeltype}''')

    # interesting pydantic issue gets hit if arbitrary_types_allowed is False
    if hasattr(modeltype, '__pydantic_config__'):
        config = getattr(modeltype, '__pydantic_config__')
        config['arbitrary_types_allowed'] = True
    else:
        config = pydantic.ConfigDict()
        config['arbitrary_types_allowed'] = True
        setattr(modeltype, '__pydantic_config__', config)
    PydanticModel = pydantic.TypeAdapter(modeltype)

    def annotation_schema():
        schema = PydanticModel.json_schema()
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        schema['$id'] = schema_id
        return schema

    class Annotation:
        'Generated annotation class'
        schema = annotation_schema()

        def __init__(self, parent):
            self.parent = parent

        def origin(self):
            return self.parent

        def as_json(self):
            return PydanticModel.dump_python(getattr(self.parent, member))

    def decorate_class(klass):
        if hasattr(klass, 'annotations'):
            old_annotations = klass.annotations
        else:
            old_annotations = None

        def annotations(self, obj):
            if old_annotations:
                annotations = old_annotations(self, obj)
            else:
                annotations = super(klass, obj).annotations(obj)
            annotation = Annotation(self)
            return annotations + (annotation,)

        klass.annotations = annotations
        return klass

    def decorate_obj(obj):
        if hasattr(obj, 'annotations'):
            old_annotations = obj.annotations
        else:
            old_annotations = None

        def annotations(self = None, origin = None):
            if old_annotations:
                annotations = old_annotations(origin)
            else:
                annotations = super(obj.__class__, obj).annotations(obj)
            annotation = Annotation(self)
            return annotations + (annotation,)

        setattr(obj, 'annotations', MethodType(annotations, obj))
        return obj

    if decorate_object:
        return decorate_obj
    else:
        return decorate_class

