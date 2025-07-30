
from collections.abc import Generator
from types import MethodType
from typing import (
    Tuple, TypeVar,
)
from typing_extensions import is_typeddict

import pydantic
from amaranth import Fragment
from amaranth.lib import meta, wiring


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
        if hasattr(obj, 'annotations'):
            old_annotations = obj.annotations
        else:
            old_annotations = None

        def annotations(self, origin , /):  # type: ignore
            if old_annotations:
                annotations = old_annotations(origin)
            else:
                annotations = super(obj.__class__, obj).annotations(obj)
            annotation = Annotation(self)
            return annotations + (annotation,)  # type: ignore

        setattr(obj, 'annotations',  MethodType(annotations, obj))
        return obj

    if decorate_object:
        return decorate_obj
    else:
        return decorate_class


def submodule_metadata(fragment: Fragment, component_name: str, recursive=False) -> Generator[Tuple[wiring.Component, str| tuple, dict]]:
    """
    Generator that finds `component_name` in `fragment` and
    then yields the ``wiring.Component``s of that component's submodule, along with their names and metadata

    Can only be run once for a given component (or its children)

    If recursive = True, then name is a tuple of the heirarchy of names
    otherwise, name is the string name of the first level component
    """

    subfrag = fragment.find_subfragment(component_name)
    design = subfrag.prepare()
    for k,v in design.elaboratables.items():
        full_name:tuple = design.fragments[design.elaboratables[k]].name
        if len(full_name) > 1:  # ignore the top component
            if recursive:
                name = full_name[1:]
            else:
                if len(full_name) != 2:
                    continue
                name = full_name[1]
            if isinstance(k, wiring.Component):
                metadata = k.metadata.as_json()['interface']
                yield k, name, metadata

