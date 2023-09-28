import inspect
from typing import Dict, NotRequired, Optional, Required, get_type_hints, is_typeddict

from ocsf_validator.errors import (
    Collector,
    InvalidMetaSchemaError,
    MissingRequiredKeyError,
    UnknownKeyError,
    UnusedAttributeError,
    UndetectableTypeError,
)
from ocsf_validator.matchers import (
    DictionaryMatcher,
    EventMatcher,
    ExtensionMatcher,
    ObjectMatcher,
)
from ocsf_validator.reader import Reader
from ocsf_validator.types import *
from ocsf_validator.type_mapping import TypeMapping
from ocsf_validator.processor import process_includes


def validate_required_keys(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    """Validate that no required keys are missing."""

    if types is None:
        types = TypeMapping(reader)

    def compare_keys(data: Dict[str, Any], defn: type, file: str):
        if hasattr(defn, "__required_keys__"):
            for k in defn.__required_keys__:
                t = leaf_type(defn, k)
                if k not in data:
                    collector.handle(MissingRequiredKeyError(k, file))
                elif t is not None and is_ocsf_type(t):
                    if isinstance(data[k], dict):
                        # dict[str, Ocsf____]
                        for k2, val in data[k]:
                            compare_keys(data[k][k2], t, file)
                    else:
                        compare_keys(data[k], t, file)

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
            """
            for k, a in defn.__annotations__.items():
                if hasattr(a, "__args__"):
                    args = a.__args__
                    for i in range(0, len(args)):
                        arg = args[i]
                        if arg == dict or arg == Dict:
                            print("found dict")
                        if hasattr(arg, "__args__"):
                            print("nested", arg.__args__)
                        print("arg", arg)
                        """

    reader.apply(validate)


def validate_no_unknown_keys(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
):
    """Validate that there are no unknown keys."""

    if types is None:
        types = TypeMapping(reader)

    def _validator(defn: type):
        def validate(reader: Reader, file: str):
            data = reader[file]
            for k in data.keys():
                if k not in defn.__annotations__:
                    collector.handle(UnknownKeyError(k, file))

        return validate

    reader.apply(_validator(OcsfObject), ObjectMatcher())
    reader.apply(_validator(OcsfEvent), EventMatcher())
    reader.apply(_validator(OcsfDictionary), DictionaryMatcher())
    reader.apply(_validator(OcsfExtension), ExtensionMatcher())


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
