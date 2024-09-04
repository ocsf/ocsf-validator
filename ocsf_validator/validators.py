import json
from pathlib import Path, PurePath
from typing import Any, Callable, Dict, List, Optional

import jsonschema
import referencing
import referencing.exceptions

from ocsf_validator.errors import (
    Collector,
    IllegalObservableTypeIDError,
    InvalidAttributeTypeError,
    InvalidMetaSchemaError,
    InvalidMetaSchemaFileError,
    MissingRequiredKeyError,
    ObservableTypeIDCollisionError,
    TypeNameCollisionError,
    UndefinedAttributeError,
    UndetectableTypeError,
    UnknownCategoryError,
    UnknownKeyError,
    UnusedAttributeError,
)
from ocsf_validator.matchers import (
    AnyMatcher,
    CategoriesMatcher,
    DictionaryMatcher,
    EventMatcher,
    ExtensionMatcher,
    ObjectMatcher,
    ProfileMatcher,
)
from ocsf_validator.processor import process_includes
from ocsf_validator.reader import Reader
from ocsf_validator.type_mapping import TypeMapping
from ocsf_validator.types import (
    ATTRIBUTES_KEY,
    CATEGORY_KEY,
    INCLUDE_KEY,
    OBSERVABLE_KEY,
    OBSERVABLES_KEY,
    TYPES_KEY,
    OcsfEvent,
    OcsfObject,
    is_ocsf_type,
    leaf_type,
)

METASCHEMA_MATCHERS = {
    "event.schema.json": EventMatcher(),
    "object.schema.json": ObjectMatcher(),
    "profile.schema.json": ProfileMatcher(),
    "categories.schema.json": CategoriesMatcher(),
    "dictionary.schema.json": DictionaryMatcher(),
    "extension.schema.json": ExtensionMatcher(),
}


def validate_required_keys(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    """Validate that no required keys are missing."""

    if types is None:
        types = TypeMapping(reader)

    def compare_keys(
        data: Dict[str, Any], defn: type, file: str, trail: list[str] = []
    ):
        if hasattr(defn, "__required_keys__"):
            for k in defn.__required_keys__:  # type: ignore
                t = leaf_type(defn, k)
                if k not in data:
                    collector.handle(MissingRequiredKeyError(k, file, defn, trail))
                elif t is not None and is_ocsf_type(t):
                    if isinstance(data[k], dict):
                        # dict[str, Ocsf____]
                        for k2, val in data[k].items():
                            if k2 != INCLUDE_KEY:
                                compare_keys(data[k][k2], t, file, trail + [k, k2])
                    else:
                        compare_keys(data[k], t, file, trail + [k])

        else:
            collector.handle(
                InvalidMetaSchemaError(
                    f"Unexpected definition {defn} used when processing {file}"
                )
            )

    def validate(reader: Reader, file: str):
        record = reader[file]
        if file not in types:
            collector.handle(UndetectableTypeError(file))
        else:
            defn = types[file]
            if not hasattr(defn, "__annotations__"):
                collector.handle(InvalidMetaSchemaError(f"{defn} is not a TypedDict"))
            compare_keys(record, defn, file)

    reader.apply(validate)


def validate_no_unknown_keys(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    """Validate that there are no unknown keys."""

    if types is None:
        types = TypeMapping(reader)

    def compare_keys(
        data: Dict[str, Any], defn: type, file: str, trail: list[str] = []
    ):
        if hasattr(defn, "__annotations__") and isinstance(data, dict):
            for k in data.keys():
                t = leaf_type(defn, k)
                if t is None:
                    collector.handle(UnknownKeyError(k, file, defn, trail))
                elif is_ocsf_type(t):
                    if hasattr(defn.__annotations__[k], "__args__"):
                        args = defn.__annotations__[k].__args__
                        if len(args) >= 2:
                            if args[-2] == str:
                                for k2, val in data[k].items():
                                    if k2 != INCLUDE_KEY:
                                        compare_keys(
                                            data[k][k2], t, file, trail + [k, k2]
                                        )
                            else:
                                ...  # what would this be?
                        else:
                            compare_keys(data[k], args[-1], file, trail + [k])
                    else:
                        compare_keys(data[k], t, file, trail + [k])

        else:
            collector.handle(
                InvalidMetaSchemaError(
                    f"Unexpected definition {defn} used when processing {file}"
                )
            )

    def validate(reader: Reader, file: str):
        record = reader[file]
        if file not in types:
            collector.handle(UndetectableTypeError(file))
        else:
            defn = types[file]
            if not hasattr(defn, "__annotations__"):
                collector.handle(InvalidMetaSchemaError(f"{defn} is not a TypedDict"))
            compare_keys(record, defn, file)

    reader.apply(validate)


def validate_include_targets(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    process_includes(reader, collector=collector, types=types, update=False)


def validate_unused_attrs(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    if types is None:
        types = TypeMapping(reader)

    # TODO: Lift validate() function out and use a TypeMapping
    def make_validator(defn: type):
        def validate(reader: Reader, key: str, accum: set[str]):
            record = reader[key]
            if ATTRIBUTES_KEY in record:
                return accum | set(
                    [k for k in record[ATTRIBUTES_KEY]]
                )  # should it be defn[attrs][k]['name'] ?
            else:
                return accum

        return validate

    attrs = reader.map(make_validator(OcsfObject), ObjectMatcher(), set())
    attrs |= reader.map(make_validator(OcsfEvent), EventMatcher(), set())

    d = reader.find("dictionary.json")

    if d is not None:
        for k in d[ATTRIBUTES_KEY]:
            if k not in attrs:
                collector.handle(UnusedAttributeError(k))


def validate_undefined_attrs(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    if types is None:
        types = TypeMapping(reader)

    EXCLUDE = ["$include"]

    dicts = []
    for d in reader.match(DictionaryMatcher()):
        dicts.append(reader[d])

    if len(dicts) == 0:
        collector.handle(InvalidMetaSchemaError())

    def validate(reader: Reader, file: str):
        record = reader[file]
        if ATTRIBUTES_KEY in record:
            for k in record[ATTRIBUTES_KEY]:
                found = False
                for d in dicts:
                    if k in d[ATTRIBUTES_KEY]:
                        found = True

                if found is False and k not in EXCLUDE:
                    collector.handle(UndefinedAttributeError(k, file))

    reader.apply(
        validate,
        AnyMatcher([ObjectMatcher(), EventMatcher(), ProfileMatcher()]),
    )


def validate_intra_type_collisions(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    if types is None:
        types = TypeMapping(reader)

    found: dict[str, dict[str, list[str]]] = {}

    def validate(reader: Reader, file: str):
        t = str(types[file])
        if t not in found:
            found[t] = {}

        # The patch extends case _always_ has the the same name as its base
        if "name" in reader[file] and not _is_patch_extends(reader[file]):
            name = reader[file]["name"]
            if name not in found[t]:
                found[t][name] = []
            else:
                collector.handle(
                    TypeNameCollisionError(name, t, file, found[t][name][0])
                )
            found[t][name].append(file)

    reader.apply(validate, AnyMatcher([ObjectMatcher(), EventMatcher()]))


def _default_get_registry(reader: Reader, base_uri: str) -> referencing.Registry:
    registry: referencing.Registry = referencing.Registry()

    for schema_file_path in reader.metaschema_path.glob("*.schema.json"):  # type: ignore
        with open(schema_file_path, "r") as file:
            schema = json.load(file)
            resource = referencing.Resource.from_contents(schema)  # type: ignore
            registry = registry.with_resource(
                base_uri + schema_file_path.name, resource=resource
            )
    return registry


def validate_metaschemas(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
    get_registry: Callable[[Reader, str], referencing.Registry] = _default_get_registry,
) -> None:
    if types is None:
        types = TypeMapping(reader)

    base_uri = "https://schemas.ocsf.io/"
    registry = get_registry(reader, base_uri)

    for metaschema, matcher in METASCHEMA_MATCHERS.items():
        try:
            schema = registry.resolver(base_uri).lookup(metaschema).contents
        except referencing.exceptions.Unresolvable as exc:
            collector.handle(
                InvalidMetaSchemaFileError(
                    f"The metaschema file for {metaschema} is invalid or missing."
                    f" Error: {type(exc).__name__}"
                )
            )
            continue

        def validate(reader: Reader, file: str) -> None:
            data = reader.contents(file)
            validator = jsonschema.Draft202012Validator(schema, registry=registry)
            errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
            for error in errors:
                collector.handle(
                    InvalidMetaSchemaError(
                        f"File at {file} does not pass metaschema validation. "
                        f"Error: {error.message} at JSON path: '{error.json_path}'"
                    )
                )

        reader.apply(validate, matcher)


def validate_attr_types(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
) -> None:
    if types is None:
        types = TypeMapping(reader)

    EXCLUDE = ["$include"]

    dicts = []
    for d in reader.match(DictionaryMatcher()):
        dicts.append(reader[d])

    if len(dicts) == 0:
        collector.handle(InvalidMetaSchemaError())

    ## Build a list of object names
    def names(reader: Reader, file: str, accum: list[str]) -> list[str]:
        if "name" in reader[file]:
            accum.append(reader[file]["name"])

        return accum

    objects: list[str] = []
    reader.map(names, ObjectMatcher(), objects)

    # Validation for each file
    def validate(reader: Reader, file: str):
        record = reader[file]
        if ATTRIBUTES_KEY in record:
            for k in record[ATTRIBUTES_KEY]:
                if k not in EXCLUDE:
                    attr = record[ATTRIBUTES_KEY][k]
                    if "type" in attr:
                        found = False

                        if attr["type"][-2:] == "_t":
                            # Scalar type; check dictionaries.
                            for d in dicts:
                                if (
                                    TYPES_KEY in d
                                    and attr["type"] in d[TYPES_KEY][ATTRIBUTES_KEY]
                                ):
                                    found = True
                        else:
                            # Object type; check objects in repository.
                            found = attr["type"] in objects

                        if found is False:
                            collector.handle(
                                InvalidAttributeTypeError(attr["type"], k, file)
                            )

    reader.apply(
        validate,
        AnyMatcher([ObjectMatcher(), EventMatcher(), ProfileMatcher()]),
    )


def validate_observables(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
) -> str:
    """
    Validate defined observable type_id values:
        * Ensure there are no collisions.
        * Ensure no definitions in "hidden" (intermediate) classes and objects.

    NOTE: This must be called _before_ merging extends to avoid incorrectly detecting
          collisions between parent and child classes and objects -- specifically
          before runner.process_includes.
    """
    observables = validate_and_get_observables(reader, collector)
    return observables_to_string(observables)


# Factored out to a function for unit testing
def observables_to_string(observables: Dict[Any, List[str]]) -> str:
    strs = ["   Observables:"]
    # Supplying key function is needed for when type_ids are incorrectly defined as
    # something other than ints
    type_ids = sorted(observables.keys(), key=_lenient_to_int)
    for tid in type_ids:
        collision = ""
        if len(observables[tid]) > 1:
            collision = "💥COLLISION💥 "
        strs.append(f'   {tid:7} →️ {collision}{", ".join(observables[tid])}')
    return "\n".join(strs)


def _lenient_to_int(value) -> int:
    try:
        return int(value)
    except ValueError:
        return -1


def validate_and_get_observables(
    reader: Reader, collector: Collector = Collector.default
) -> Dict[Any, List[str]]:
    """
    Actual validation implementation.
    This exists so unit tests can interrogate the generated `observables` dictionary.
    """
    # Map of observable type_ids to list of definitions
    observables: Dict[Any, List[str]] = {}

    def check_collision(type_id: Any, name: str, file: str) -> None:
        if type_id in observables:
            definitions = observables[type_id]
            collector.handle(
                ObservableTypeIDCollisionError(type_id, name, definitions, file)
            )
            definitions.append(name)
        else:
            observables[type_id] = [name]

    def any_attribute_has_observable(source: Dict[str, Any]) -> bool:
        # Returns true if any attribute defines an observable
        if ATTRIBUTES_KEY in source:
            for item in source[ATTRIBUTES_KEY].values():
                if OBSERVABLE_KEY in item:
                    return True
        return False

    def check_attributes(
        source: Dict[str, Any], name_fn: Callable[[str, Dict[str, Any]], str], file: str
    ):
        if ATTRIBUTES_KEY in source:
            for a_key, item in source[ATTRIBUTES_KEY].items():
                if OBSERVABLE_KEY in item:
                    check_collision(item[OBSERVABLE_KEY], name_fn(a_key, item), file)

    def validate_dictionaries(reader: Reader, file: str) -> None:
        if TYPES_KEY in reader[file]:
            check_attributes(
                reader[file][TYPES_KEY],
                lambda a_key, item: f'"{a_key}" (Dictionary Type)',
                file,
            )

        check_attributes(
            reader[file],
            lambda a_key, item: f'"{a_key}" (Dictionary Attribute)',
            file,
        )

    def validate_classes(reader: Reader, file: str) -> None:
        # Classes do not have top-level "observable" attribute -- you can't specify an
        # entire class as an observable.

        # Check for illegal definition in "hidden" classes. Hidden (or "intermediate")
        # classes are those that are not a patch extends case, the name isn't
        # "base_class", and class doesn't have a "uid".
        if (
            not _is_patch_extends(reader[file])
            and "base_event" != reader[file].get("name")
            and "uid" not in reader[file]
        ):
            if any_attribute_has_observable(reader[file]):
                cause = (
                    f"Illegal definition of one or more attributes with"
                    f' "{OBSERVABLE_KEY}" in hidden class, file "{file}": defining'
                    f" attribute observables in a hidden class (classes other than"
                    f' "base_event" without a "uid") causes collisions in child'
                    f" classes. Instead define observables (of any kind) in non-hidden"
                    f" child classes."
                )
                collector.handle(IllegalObservableTypeIDError(cause))

            if OBSERVABLES_KEY in reader[file]:
                cause = (
                    f'Illegal "{OBSERVABLES_KEY}" definition in hidden class, file'
                    f' "{file}": defining attribute path based observables in a hidden'
                    f' class (classes other than "base_event" without a "uid") causes'
                    f" collisions in child classes. Instead define observables (of any"
                    f" kind) in non-hidden child classes."
                )
                collector.handle(IllegalObservableTypeIDError(cause))

        # Check class-specific attributes
        check_attributes(
            reader[file],
            lambda a_key, item: f"{_item_name(reader[file])} class: {a_key}"
            f" (Class-Specific Attribute)",
            file,
        )

        # Check class-specific attribute path observables
        if OBSERVABLES_KEY in reader[file]:
            for attribute_path in reader[file][OBSERVABLES_KEY]:
                check_collision(
                    reader[file][OBSERVABLES_KEY][attribute_path],
                    f"{_item_name(reader[file])} class: {attribute_path}"
                    f" (Class-Specific Attribute Path)",
                    file,
                )

    def validate_objects(reader: Reader, file: str) -> None:
        # Special-case: the "observable" object model's type_id enum has the base for
        # observable type_id typically defining 0: "Unknown" and 99: "Other", which are
        # otherwise not defined.
        if (
            reader[file].get("name") == "observable"
            and ATTRIBUTES_KEY in reader[file]
            and "type_id" in reader[file][ATTRIBUTES_KEY]
            and "enum" in reader[file][ATTRIBUTES_KEY]["type_id"]
        ):
            enum_dict = reader[file][ATTRIBUTES_KEY]["type_id"]["enum"]
            for observable_type_id_str, enum in enum_dict.items():
                name = enum.get("caption", f"Observable enum {observable_type_id_str}")
                check_collision(int(observable_type_id_str), name, file)

        # Check for illegal definition in "hidden" objects. Hidden (or "intermediate")
        # objects are those that are not a patch extends case, and the name has a
        # leading underscore.
        if (
            not _is_patch_extends(reader[file])
            and "name" in reader[file]
            and PurePath(reader[file]["name"]).name.startswith("_")
        ):
            if OBSERVABLE_KEY in reader[file]:
                cause = (
                    f'Illegal "{OBSERVABLE_KEY}" definition in hidden object,'
                    f' file "{file}": defining top-level observable in a hidden'
                    f" object (name with leading underscore) causes collisions"
                    f" in child objects. Instead define observables (of any kind) in"
                    f" non-hidden child objects."
                )
                collector.handle(IllegalObservableTypeIDError(cause))

            if any_attribute_has_observable(reader[file]):
                cause = (
                    f"Illegal definition of one or more attributes with"
                    f' "{OBSERVABLE_KEY}" in hidden object, file "{file}": defining'
                    f" attribute observables in a hidden object (name with leading"
                    f" underscore) causes collisions in child objects. Instead define"
                    f" observables (of any kind) in non-hidden child objects."
                )
                collector.handle(IllegalObservableTypeIDError(cause))

        # Check top-level observable -- entire object is an observable
        if OBSERVABLE_KEY in reader[file]:
            check_collision(
                reader[file][OBSERVABLE_KEY],
                f"{_item_name(reader[file])} (Object)",
                file,
            )

        # Check object-specific attributes
        check_attributes(
            reader[file],
            lambda a_key, item: f"{_item_name(reader[file])} object: {a_key}"
            f" (Object-Specific Attribute)",
            file,
        )

    reader.apply(validate_dictionaries, DictionaryMatcher())
    reader.apply(validate_classes, EventMatcher())
    reader.apply(validate_objects, ObjectMatcher())

    return observables


def _item_name(item):
    if _is_patch_extends(item):
        suffix = " [patch extends]"
    else:
        suffix = ""
    name = item.get("name")
    if name:
        return f'"{name}"{suffix}'
    extends = item.get("extends")
    if extends:
        return f'"{extends}"{suffix}'
    return f"<unknown>{suffix}"


def _is_patch_extends(item):
    """
    Returns True if class or object is a "special" patch extends, which allows
    extensions to modify core schema classes and objects.
    """
    name = item.get("name")
    if name is None:
        name = item.get("extends")
    return name == item.get("extends")


def validate_event_categories(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    # Initialize categories list with "other" since it isn't defined in categories.json
    categories = {"other"}

    def gather_categories(reader: Reader, file: str) -> None:
        if ATTRIBUTES_KEY in reader[file]:
            categories.update(reader[file][ATTRIBUTES_KEY].keys())

    def validate_classes(reader: Reader, file: str) -> None:
        if (
            CATEGORY_KEY in reader[file]
            and reader[file][CATEGORY_KEY] not in categories
        ):
            collector.handle(UnknownCategoryError(reader[file][CATEGORY_KEY], file))

    reader.apply(gather_categories, CategoriesMatcher())
    reader.apply(validate_classes, EventMatcher())
