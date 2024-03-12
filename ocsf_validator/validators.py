import json
from pathlib import Path, PurePath
from typing import Callable

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
    UnknownKeyError,
    UnusedAttributeError,
)
from ocsf_validator.matchers import (
    AnyMatcher,
    CategoriesMatcher,
    DictionaryMatcher,
    EventMatcher,
    ExtensionMatcher,
    IncludeMatcher,
    ObjectMatcher,
    ProfileMatcher,
)
from ocsf_validator.processor import process_includes
from ocsf_validator.reader import Reader
from ocsf_validator.type_mapping import TypeMapping
from ocsf_validator.types import *


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
        AnyMatcher(
            [ObjectMatcher(), EventMatcher(), ProfileMatcher(), IncludeMatcher()]
        ),
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

        if "name" in reader[file]:
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
    registry = referencing.Registry()
    for schema_file_path in (reader.base_path / "metaschema").rglob("*.schema.json"):
        with open(schema_file_path, "r") as file:
            schema = json.load(file)
            resource = referencing.Resource.from_contents(schema)
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
    matchers = {
        "event.schema.json": EventMatcher(),
        "include.schema.json": IncludeMatcher(),
        "object.schema.json": ObjectMatcher(),
        "profile.schema.json": ProfileMatcher(),
        "categories.schema.json": CategoriesMatcher(),
        "dictionary.schema.json": DictionaryMatcher(),
        "extension.schema.json": ExtensionMatcher(),
    }

    for metaschema, matcher in matchers.items():
        try:
            schema = registry.resolver(base_uri).lookup(metaschema).contents
        except referencing.exceptions.Unresolvable as exc:
            collector.handle(
                InvalidMetaSchemaFileError(
                    f"The metaschema file for {metaschema} is invalid or missing. Error: {type(exc).__name__}"
                )
            )
            continue

        def validate(reader: Reader, file: str) -> None:
            with open(Path(reader.base_path, file), "r") as f:
                data = json.load(f)
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
        AnyMatcher(
            [ObjectMatcher(), EventMatcher(), ProfileMatcher(), IncludeMatcher()]
        ),
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

    NOTE: This must be called _before_ merging extends to avoid incorrectly detecting collisions between
          parent and child classes and objects -- specifically before runner.process_includes.
    """
    # Map of observables type_ids to list of definitions
    observables: Dict[int, list[str]] = {}

    def check_collision(type_id, name, file):
        if type_id in observables:
            definitions = observables[type_id]
            collector.handle(
                ObservableTypeIDCollisionError(type_id, name, definitions, file)
            )
            definitions.append(name)
        else:
            observables[type_id] = [name]

    def check_item_maybe_observable(item, kind, file):
        if OBSERVABLE_KEY in item:
            type_id = item[OBSERVABLE_KEY]
            name = f"{item.get('caption')} ({kind})"
            check_collision(type_id, name, file)

    def validate_dictionaries(reader: Reader, file: str):
        if TYPES_KEY in reader[file] and ATTRIBUTES_KEY in reader[file][TYPES_KEY]:
            for t_key in reader[file][TYPES_KEY][ATTRIBUTES_KEY]:
                check_item_maybe_observable(
                    reader[file][TYPES_KEY][ATTRIBUTES_KEY][t_key],
                    "Dictionary Type",
                    file,
                )

        if ATTRIBUTES_KEY in reader[file]:
            for a_key in reader[file][ATTRIBUTES_KEY]:
                check_item_maybe_observable(
                    reader[file][ATTRIBUTES_KEY][a_key], "Dictionary Attribute", file
                )

    def validate_objects(reader: Reader, file: str):
        # Only check for illegal definition in objects with "name"
        # (ignore weird objects with no name that do some kind of reverse inheritance)
        # and
        if (
            "name" in reader[file]
            and PurePath(file).name.startswith("_")
            and OBSERVABLE_KEY in reader[file]
        ):
            cause = (
                f'Illegal "{OBSERVABLE_KEY}" definition in hidden object, file "{file}":'
                f" defining observable in a hidden object (name with leading underscore)"
                f" causes collisions in child objects"
            )
            collector.handle(IllegalObservableTypeIDError(cause))

        # Check for collisions in all objects
        check_item_maybe_observable(reader[file], "Object", file)

    def validate_classes(reader: Reader, file: str):
        # Only check for illegal definition in classes with "name"
        # (ignore weird classes with no name that do some kind of reverse inheritance)
        if (
            "name" in reader[file]
            and "base_event" != reader[file].get("name")
            and "uid" not in reader[file]
            and OBSERVABLES_KEY in reader[file]
        ):
            cause = (
                f'Illegal "{OBSERVABLES_KEY}" definition in hidden class, file "{file}":'
                f' defining observables in a hidden class (classes other than "base_event" without a "uid")'
                f" causes collisions in child classes"
            )
            collector.handle(IllegalObservableTypeIDError(cause))

        # Check for collisions in all classes
        if OBSERVABLES_KEY in reader[file]:
            for attribute_path in reader[file][OBSERVABLES_KEY]:
                type_id = reader[file][OBSERVABLES_KEY][attribute_path]
                name = f"{reader[file]['caption']} Class: {attribute_path} (Class-Specific)"
                check_collision(type_id, name, file)

    reader.apply(validate_dictionaries, DictionaryMatcher())
    reader.apply(validate_objects, ObjectMatcher())
    reader.apply(validate_classes, EventMatcher())

    strs = ["   Observables:"]
    type_ids = sorted(observables.keys())
    for tid in type_ids:
        collision = ""
        if len(observables[tid]) > 1:
            collision = "💥COLLISION💥 "
        strs.append(f'   {tid:6} →️ {collision}{", ".join(observables[tid])}')
    return "\n".join(strs)
