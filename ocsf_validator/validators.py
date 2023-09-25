import inspect
from typing import Dict, NotRequired, Optional, Required, get_type_hints, is_typeddict

from ocsf_validator.errors import (
    Collector,
    InvalidMetaSchemaError,
    MissingRequiredKeyError,
    UnknownKeyError,
)
from ocsf_validator.processors import (
    apply_include,
    apply_inheritance,
    apply_profiles,
    find_attrs,
)
from ocsf_validator.reader import MatchMode, Reader
from ocsf_validator.types import *


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

    reader.apply(_validator(OcsfObject), "objects/*", MatchMode.GLOB)
    reader.apply(
        _validator(OcsfExtension), "extensions/*/extension.json", MatchMode.GLOB
    )


def validate_no_unknown_keys(reader: Reader, collector: Collector = Collector.default):
    """Validate that there are no unknown keys."""

    def _validator(defn: type):
        def validate(reader: Reader, file: str):
            data = reader[file]
            for k in data.keys():
                if k not in defn.__annotations__:
                    collector.handle(UnknownKeyError(k, file))

        return validate

    reader.apply(_validator(OcsfObject), "objects/*", MatchMode.GLOB)
    reader.apply(
        _validator(OcsfExtension), "extensions/*/extension.json", MatchMode.GLOB
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
