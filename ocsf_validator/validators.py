import inspect
from typing import (Dict, NotRequired, Optional, Required, get_type_hints,
                    is_typeddict)

from ocsf_validator.errors import (Collector, InvalidMetaSchemaError,
                                   MissingRequiredKeyError, UnknownKeyError,
                                   UnusedAttributeError)
from ocsf_validator.processors import (apply_include, apply_inheritance,
                                       apply_profiles, find_attrs)
from ocsf_validator.reader import Reader
from ocsf_validator.types import *
from ocsf_validator.matchers import ObjectMatcher, EventMatcher, ExtensionMatcher, DictionaryMatcher


def validate_required_keys(reader: Reader, collector: Collector = Collector.default):
    """Validate that no required keys are missing."""

    def compare_keys(data: Dict[str, Any], defn: type, file: str):
        if hasattr(defn, "__required_keys__"):
            for k in defn.__required_keys__:
                if k not in data:
                    collector.handle(MissingRequiredKeyError(k, file))
        else:
            collector.handle(
                InvalidMetaSchemaError(
                    f"Unexpected definition {defn} used when processing {file}"
                )
            )

    def _validator(defn: type):
        attrs_key = find_attrs(defn)

        def validate(reader: Reader, file: str):
            compare_keys(reader[file], defn, file)

            if attrs_key is not None:
                for k, attr in reader[file][attrs_key].items():
                    compare_keys(reader[file][attrs_key], OcsfAttr, file)

        return validate

    reader.apply(_validator(OcsfObject), ObjectMatcher())
    reader.apply(_validator(OcsfEvent), EventMatcher())
    reader.apply(_validator(OcsfExtension), ExtensionMatcher())


def validate_no_unknown_keys(reader: Reader, collector: Collector = Collector.default):
    """Validate that there are no unknown keys."""

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
    reader.apply(
        _validator(OcsfExtension), ExtensionMatcher()
    )


def validate_includes(reader: Reader, collector: Collector = Collector.default):
    # Raises MissingIncludeError
    apply_include(reader, update=False, collector=collector)


def validate_inheritance(reader: Reader, collector: Collector = Collector.default):
    # Raises MissingBaseError
    apply_inheritance(reader, update=False, collector=collector)


def validate_profiles(
    reader: Reader,
    profiles: Optional[list[str]] = None,
    collector: Collector = Collector.default,
):
    # Raises MissingProfileError
    apply_profiles(reader, update=False, collector=collector)


def validate_unused_attrs(reader: Reader, collector: Collector = Collector.default):
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
    attrs |= reader.map(
        make_validator(OcsfEvent), EventMatcher(), set()
    )

    d = reader.find("dictionary.json")
    attr_key = find_attrs(OcsfDictionary)

    for k in d[attr_key]:
        if k not in attrs:
            collector.handle(UnusedAttributeError(k))
