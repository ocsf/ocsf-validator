import inspect
from typing import Dict, NotRequired, Required, get_type_hints, is_typeddict

from ocsf_validator.errors import (
    InvalidMetaSchemaError,
    MissingRequiredKeyError,
    UnknownKeyError,
)
from ocsf_validator.processors import find_attrs, apply_include, apply_extends, apply_profiles
from ocsf_validator.reader import Reader, MatchMode
from ocsf_validator.types import *

# [X] Required keys (including nested in attrs)
# [X] No unknown keys
# [X] Include files (and base records and profiles) exist
# [ ] Categories match directories in events
# [ ] Unused dictionary items
# [ ] Unused enums
# [ ] Valid types for attributes
# [ ] Type Matching
# [ ] Name collisions between extensions
# [ ] Name collisions between objects and events


def validate_required_keys(reader: Reader):
    """Validate that no required keys are missing."""

    def compare_keys(data: Dict[str, Any], defn: type, file: str):
        if hasattr(defn, "__required_keys__"):
            for k in defn.__required_keys__:
                if k not in data:
                    raise MissingRequiredKeyError(k, file)
        else:
            raise InvalidMetaSchemaError(
                f"Unexpected definition {defn} used when processing {file}"
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
    reader.apply(_validator(OcsfExtension), "extensions/*/extension.json", MatchMode.GLOB)


def validate_no_unknown_keys(reader: Reader):
    """Validate that there are no unknown keys."""

    def _validator(defn: type):
        def validate(reader: Reader, file: str):
            data = reader[file]
            for k in data.keys():
                if k not in defn.__annotations__:
                    raise UnknownKeyError(k, file)

        return validate

    reader.apply(_validator(OcsfObject), "objects/*", MatchMode.GLOB)
    reader.apply(_validator(OcsfExtension), "extensions/*/extension.json", MatchMode.GLOB)


def validate_includes(reader: Reader):
    # Raises MissingIncludeError
    apply_include(reader, update = False)

def validate_extends(reader: Reader):
    # Raises MissingBaseError
    apply_extends(reader, update = False)

def validate_profiles(reader: Reader):
    # Raises MissingProfileError
    apply_profiles(reader, update = False)

