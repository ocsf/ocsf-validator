"""Validate OCSF Schema definitions.

"""

import traceback
from argparse import ArgumentParser
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional
from termcolor import colored

import ocsf_validator.errors as errors
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
    validate_unused_attrs,
)


class Severity(IntEnum):
    IGNORE = 0
    WARN = 1
    ERROR = 2
    CRASH = 3


@dataclass
class SeverityOptions:
    invalid_path: int = Severity.CRASH
    """The OCSF Schema path could not be found or is horribly wrong."""

    invalid_metaschema: int = Severity.CRASH
    """The metaschema defined in this validator appears to be invalid."""

    missing_include: int = Severity.ERROR
    """An `$include` target is missing."""

    missing_profile: int = Severity.ERROR
    """A `profiles` target is missing."""

    missing_inheritance: int = Severity.ERROR
    """An `extends` inheritance target is missing."""

    missing_key: int = Severity.ERROR
    """A required key is missing."""

    unknown_key: int = Severity.WARN
    """An unrecognized key was found."""

    unused_attribute: int = Severity.WARN
    """An attribute in `dictionary.json` is unused."""

    def severity(self, err: errors.ValidationError):
        match type(err):
            case errors.MissingRequiredKeyError:
                return self.missing_key
            case errors.UnknownKeyError:
                return self.unknown_key
            case errors.MissingIncludeError:
                return self.missing_include
            case errors.MissingProfileError:
                return self.missing_profile
            case errors.MissingBaseError:
                return self.missing_inheritance
            case errors.UnusedAttributeError:
                return self.unused_attribute
            case errors.InvalidMetaSchemaError:
                return self.invalid_metaschema
            case errors.InvalidBasePathError:
                return self.invalid_path
            case _:
                return Severity.IGNORE

@dataclass
class ValidatorOptions(SeverityOptions):
    """Configure validator behavior."""

    base_path: str = "."
    """The base path of the schema."""

    extensions: bool = True
    """Include the contents of extensions."""

    inheritance: bool = True
    """Include the contents of extends directives."""

    profiles: bool = True
    """Include the contents of profiles."""

    includes: bool = True
    """Include the contents of $include directives."""

    allowed_profiles: Optional[list[str]] = None
    """White list of profiles to include in validation. If None, all profiles
    are inspected."""



class ValidationRunner:
    def __init__(self, pathOrOptions: str | ValidatorOptions):
        if isinstance(pathOrOptions, str):
            options = ValidatorOptions(base_path=pathOrOptions)
        else:
            options = pathOrOptions

        self.options = options

    def validate(self):
        exit_code = 0
        messages: dict[str, dict[int, set[str]]] = {}
        collector = errors.Collector(throw=False)

        def test(label: str, code: callable, severity: int = -1):
            if severity > Severity.IGNORE:
                message: str = ""
                code()

                if len(collector) > 0:
                    print(colored("FAILED", "red"), end="")
                    for err in collector.exceptions():
                        severity = self.options.severity(err)

                        if label not in messages:
                            messages[label] = {}
                        if severity not in messages[label]:
                            messages[label][severity] = set()
                        messages[label][severity].add(str(err))

                        match severity:
                            case Severity.WARN:
                                ...
                            case Severity.ERROR:
                                exit_code = 1
                            case Severity.CRASH:
                                exit(10)

                    collector.flush()

                else:
                    print(colored("SUCCESS", "green"), end="")

                print(" ", colored(label, "white"))

        try:
            print(f"Validating OCSF schema at {self.options.base_path}")

            # Setup the reader
            opts = ReaderOptions(
                base_path=Path(self.options.base_path),
                read_extensions=self.options.extensions,
            )
            try:
                reader = FileReader(opts)
            except errors.ValidationError as err:
                collector.handle(err)
            test("Schema can be loaded", lambda: None, Severity.CRASH)

            # Validate dependencies
            test(
                "Valid `$include` targets",
                lambda: validate_includes(reader, collector),
                self.options.missing_include
            )

            test(
                "Valid `extends` targets",
                lambda: validate_inheritance(reader, collector),
                self.options.missing_inheritance
            )

            test(
                "Valid `profiles` targets",
                lambda: validate_profiles(
                    reader, self.options.allowed_profiles, collector=collector
                ),
                self.options.missing_profile
            )

            # Process dependencies
            if self.options.includes:
                apply_include(reader, collector=collector)

            if self.options.inheritance:
                apply_inheritance(reader, collector=collector)

            if self.options.profiles:
                apply_profiles(
                    reader, self.options.allowed_profiles, collector=collector
                )

            # Any errors since the last test were duplicates; ignore them
            collector.flush()

            # Validate keys
            test(
                "Required keys are present",
                lambda: validate_required_keys(reader, collector),
                self.options.missing_key,
            )
            test(
                "No unrecognized keys",
                lambda: validate_no_unknown_keys(reader, collector),
                self.options.unknown_key,
            )

            test("No unused attributes",
                 lambda: validate_unused_attrs(reader, collector),
                 self.options.unused_attribute,
            )


        except Exception as err:
            print("Encountered an unexpected exception:")
            traceback.print_exception(err)

        finally:
            labels = {Severity.WARN: "WARNING", Severity.ERROR: "ERROR",
                          Severity.CRASH: "HALT"}
            colors = {Severity.WARN: "yellow", Severity.ERROR: "red", Severity.CRASH: "magenta"}

            for k in messages:
                if len(messages[k].items()) > 0:
                    print("")
                    print(colored("Results for test:", "white"), k)

                    for s in labels:
                        if s in messages[k]:
                            for error in messages[k][s]:
                                print(" ", colored(labels[s], colors[s]), error)

        print("")
        exit(exit_code)


if __name__ == "__main__":
    parser = ArgumentParser(prog="ocsf-validator", description="OCSF Schema Validation")
    parser.add_argument("path", help="The OCSF schema root directory", action="store")
    args = parser.parse_args()

    opts = ValidatorOptions(base_path=args.path)

    validator = ValidationRunner(opts)

    validator.validate()
