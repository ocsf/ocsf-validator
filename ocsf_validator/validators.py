import inspect
from typing import (Dict, NotRequired, Optional, Required, get_type_hints,
                    is_typeddict)

from ocsf_validator.errors import (Collector, InvalidMetaSchemaError,
                                   MissingRequiredKeyError,
                                   UndetectableTypeError, UnknownKeyError,
                                   UnusedAttributeError)
from ocsf_validator.matchers import (DictionaryMatcher, EventMatcher,
                                     ExtensionMatcher, ObjectMatcher)
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
            for k in defn.__required_keys__:
                t = leaf_type(defn, k)
                if k not in data:
                    collector.handle(MissingRequiredeyError(k, file, defn, trail))
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

                    """if isinstance(data[k], dict):
                        # dict[str, Ocsf____]
                        for k2, val in data[k].items():
                            if k2 != INCLUDE_KEY:
                                compare_keys(data[k][k2], t, file, trail + [k, k2])
                    else:
                        print("leaf")
                        compare_keys(data[k], t, file, trail + [k])
                        """

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

    def make_validator(defn: type):
        attrs = find_attrs(defn)

        def validate(reader: Reader, key: str, accum: set[str]):
            record = reader[key]
            if attrs is not None and attrs in record:
                return accum | set(
                    [k for k in record[attrs]]
                )  # should it be defn[attrs][k]['name'] ?
            else:
                return accum

        return validate

    attrs = reader.map(make_validator(OcsfObject), ObjectMatcher(), set())
    attrs |= reader.map(make_validator(OcsfEvent), EventMatcher(), set())

    d = reader.find("dictionary.json")
    attr_key = find_attrs(OcsfDictionary)

    for k in d[attr_key]:
        if k not in attrs:
            collector.handle(UnusedAttributeError(k))
