"""Validate OCSF Schema definitions.

"""

import traceback
from argparse import ArgumentParser
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional

from termcolor import colored

from ocsf_validator.errors import *
from ocsf_validator.processors import (
    apply_attributes,
    apply_include,
    apply_inheritance,
    apply_profiles,
)
from ocsf_validator.reader import FileReader, ReaderOptions
from ocsf_validator.validators import (
    validate_includes,
    validate_inheritance,
    validate_no_unknown_keys,
    validate_profiles,
    validate_required_keys,
)


class Severity(IntEnum):
    WARN = 1
    FAIL = 2
    CRASH = 3


@dataclass
class ValidatorOptions:
    """Configure validator behavior."""

    """The base path of the schema."""
    base_path: str

    """Validate the contents of extensions."""
    validate_extensions: bool = True

    """Validate the contents of extends directives."""
    validate_inheritance: bool = True

    """Validate the contents of profiles."""
    validate_profiles: bool = True

    """Validate the contents of includes."""
    validate_includes: bool = True

    """White list of profiles to include in validation. If None, all profiles
    are inspected."""
    allowed_profiles: Optional[list[str]] = None

    invalid_path_level: int = Severity.CRASH
    invalid_metaschema_level: int = Severity.CRASH
    missing_include_level: int = Severity.FAIL
    missing_profile_level: int = Severity.FAIL
    missing_inheritance_level: int = Severity.FAIL
    missing_key_level: int = Severity.FAIL
    unknown_key_level: int = Severity.WARN


class ValidationRunner:
    def __init__(self, pathOrOptions: str | ValidatorOptions):
        if isinstance(pathOrOptions, str):
            options = ValidatorOptions(base_path=pathOrOptions)
        else:
            options = pathOrOptions

        self.severity = {
            InvalidBasePathError: options.invalid_path_level,
            InvalidMetaSchemaError: options.invalid_metaschema_level,
            MissingRequiredKeyError: options.missing_key_level,
            UnknownKeyError: options.unknown_key_level,
            MissingIncludeError: options.missing_include_level,
            MissingProfileError: options.missing_profile_level,
            MissingBaseError: options.missing_inheritance_level,
        }
        self.options = options

    def validate(self):
        exit_code = 0
        messages: dict[str, dict[int, set[str]]] = {}
        collector = Collector(throw=False)

        def test(label: str, code: callable):
            message: str = ""
            code()

            if len(collector) > 0:
                print(colored("FAILED", "red", attrs=["bold"]), end="")
                for err in collector.exceptions():
                    severity = self.severity[type(err)]

                    if label not in messages:
                        messages[label] = {}
                    if severity not in messages[label]:
                        messages[label][severity] = set()
                    messages[label][severity].add(str(err))

                    match severity:
                        case Severity.WARN:
                            ...
                        case Severity.FAIL:
                            exit_code = 1
                        case Severity.CRASH:
                            exit(10)

                collector.flush()

            else:
                print(colored("SUCCESS", "green", attrs=["bold"]), end="")

            print(" ", colored(label, "white"))

        try:
            opts = ReaderOptions(
                base_path=Path(self.options.base_path),
                read_extensions=self.options.validate_extensions,
            )
            try:
                reader = FileReader(opts)
            except ValidationError as err:
                collector.handle(err)
            test("Schema can be loaded", lambda: None)

            # Validate dependencies
            if self.options.validate_includes:
                test(
                    "Valid `$include` targets",
                    lambda: validate_includes(reader, collector),
                )

            if self.options.validate_inheritance:
                test(
                    "Valid `extends` targets",
                    lambda: validate_inheritance(reader, collector),
                )

            if self.options.validate_profiles:
                test(
                    "Valid `profiles` targets",
                    lambda: validate_profiles(
                        reader, self.options.allowed_profiles, collector=collector
                    ),
                )

            # Process dependencies
            if self.options.validate_includes:
                apply_include(reader, collector=collector)

            if self.options.validate_inheritance:
                apply_inheritance(reader, collector=collector)

            if self.options.validate_profiles:
                apply_profiles(
                    reader, self.options.allowed_profiles, collector=collector
                )

            # Any errors since the last test were duplicates; ignore them
            collector.flush()

            # Validate keys
            test(
                "Required keys are present",
                lambda: validate_required_keys(reader, collector),
            )
            test(
                "No unrecognized keys",
                lambda: validate_no_unknown_keys(reader, collector),
            )

        except Exception as err:
            print("Encountered an unexpected exception:")
            traceback.print_exception(err)

        finally:
            severities = {Severity.WARN: "WARNING", Severity.FAIL: "ERROR",
                          Severity.CRASH: "HALT"}

            for k in messages:
                if len(messages[k].items()) > 0:
                    print("")
                    print(colored(k, "white", attrs=["bold"]))

                    for s in severities:
                        if s in messages[k]:
                            for error in messages[k][s]:
                                print(colored(severities[s], "white"), error)

        print("")
        exit(exit_code)


if __name__ == "__main__":
    parser = ArgumentParser(prog="ocsf-validator", description="OCSF Schema Validation")
    parser.add_argument("path", help="The OCSF schema root directory", action="store")
    args = parser.parse_args()

    opts = ValidatorOptions(args.path)

    validator = ValidationRunner(opts)

    validator.validate()
