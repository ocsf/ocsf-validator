"""Validate OCSF Schema definitions.

"""

import traceback
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Callable

from termcolor import colored

import ocsf_validator.errors as errors
from ocsf_validator.processor import process_includes
from ocsf_validator.reader import FileReader, ReaderOptions
from ocsf_validator.type_mapping import TypeMapping
from ocsf_validator.validators import (
    validate_attr_types,
    validate_include_targets,
    validate_intra_type_collisions,
    validate_metaschemas,
    validate_no_unknown_keys,
    validate_observables,
    validate_required_keys,
    validate_undefined_attrs,
    validate_unused_attrs,
)


class Severity(IntEnum):
    INFO = 0
    WARN = 1
    ERROR = 2
    FATAL = 3


@dataclass
class ValidatorOptions:
    """Configure validator behavior."""

    base_path: str = "."
    """The base path of the schema."""

    extensions: bool = True
    """Include the contents of extensions."""

    strict: bool = False
    """When True, exit with a non-zero exit code when warnings are encountered."""

    show_info: bool = False
    """Show informational messages."""

    invalid_path: int = Severity.FATAL
    """The OCSF Schema path could not be found or is horribly wrong."""

    invalid_metaschema: int = Severity.FATAL
    """The metaschema defined in this validator appears to be invalid."""

    missing_include: int = Severity.ERROR
    """An `$include` target is missing."""

    missing_profile: int = Severity.ERROR
    """A `profiles` target is missing."""

    missing_inheritance: int = Severity.ERROR
    """An `extends` inheritance target is missing."""

    imprecise_inheritance: int = Severity.INFO
    """An `extends` inheritance target is resolvable but imprecise and possibly ambiguous."""

    missing_key: int = Severity.ERROR
    """A required key is missing."""

    unknown_key: int = Severity.ERROR
    """An unrecognized key was found."""

    unused_attribute: int = Severity.WARN
    """An attribute in `dictionary.json` is unused."""

    self_inheritance: int = Severity.WARN
    """Attempting to `extend` the current record."""

    redundant_profile_include: int = Severity.INFO
    """Redundant profiles and $include target."""

    undetectable_type: int = Severity.WARN
    """Unable to detect type of file."""

    include_type_mismatch: int = Severity.WARN
    """Unexpected include type."""

    intra_type_name_collision: int = Severity.WARN
    """Same name used multiple times within a type."""

    undefined_attribute: int = Severity.WARN
    """Attributes used in a record but not defined in `dictionary.json`."""

    invalid_metaschema_file: int = Severity.ERROR
    """A JSON schema metaschema file is missing or invalid."""

    invalid_attr_types: int = Severity.ERROR
    """Attribute type is invalid."""

    illegal_observable: int = Severity.ERROR
    """Observable type_id illegally defined."""

    observable_collision: int = Severity.ERROR
    """Colliding observable type_id defined."""

    def severity(self, err: Exception):
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
            case errors.ImpreciseBaseError:
                return self.imprecise_inheritance
            case errors.SelfInheritanceError:
                return self.self_inheritance
            case errors.RedundantProfileIncludeError:
                return self.redundant_profile_include
            case errors.UndetectableTypeError:
                return self.undetectable_type
            case errors.IncludeTypeMismatchError:
                return self.include_type_mismatch
            case errors.TypeNameCollisionError:
                return self.intra_type_name_collision
            case errors.UndefinedAttributeError:
                return self.undefined_attribute
            case errors.InvalidMetaSchemaFileError:
                return self.invalid_metaschema_file
            case errors.InvalidAttributeTypeError:
                return self.invalid_attr_types
            case errors.IllegalObservableTypeIDError:
                return self.illegal_observable
            case errors.ObservableTypeIDCollisionError:
                return self.observable_collision
            case _:
                return Severity.INFO


class ValidationRunner:
    def __init__(self, pathOrOptions: str | ValidatorOptions):
        if isinstance(pathOrOptions, str):
            options = ValidatorOptions(base_path=pathOrOptions)
        else:
            options = pathOrOptions

        self.options = options

    def txt_fail(self, text: str):
        return colored(text, "red")

    def txt_warn(self, text: str):
        return colored(text, "yellow")

    def txt_crash(self, text: str):
        return colored(text, "black", "on_red")

    def txt_info(self, text: str):
        return colored(text, "blue")

    def txt_pass(self, text: str):
        return colored(text, "green")

    def txt_highlight(self, text: str):
        return colored(text, "light_grey", "on_cyan")

    def txt_emphasize(self, text: str):
        return colored(text, "white")

    def txt_label(self, severity: int):
        match severity:
            case Severity.INFO:
                return self.txt_info("INFO")
            case Severity.WARN:
                return self.txt_warn("WARNING")
            case Severity.ERROR:
                return self.txt_fail("ERROR")
            case Severity.FATAL:
                return self.txt_crash("FATAL")
            case _:
                return self.txt_emphasize("???")

    def validate(self):
        exit_code = 0
        messages: dict[str, dict[int, set[str]]] = {}
        collector = errors.Collector(throw=False)

        def test(label: str, code: Callable):
            failures: int = 0
            message = code()

            if label not in messages:
                messages[label] = {}
                print("")
                print(self.txt_info("TESTING") + ":", self.txt_emphasize(label))

            for err in collector.exceptions():
                severity = self.options.severity(err)

                if severity not in messages[label]:
                    messages[label][severity] = set()

                messages[label][severity].add(str(err))
                if severity > Severity.INFO or self.options.show_info:
                    if severity > Severity.INFO:
                        failures += 1
                    print("  ", self.txt_label(severity) + ":", err)

                if severity == Severity.FATAL:
                    exit(2)

            if failures == 0:
                print("  ", self.txt_pass("PASS") + ":", "No problems identified.")
            collector.flush()

            if message:
                print(message)

        try:
            print(self.txt_emphasize("===[ OCSF Schema Validator ]==="))
            print(
                "Validating OCSF Schema at", self.txt_highlight(self.options.base_path)
            )

            # Setup the reader
            opts = ReaderOptions(
                base_path=Path(self.options.base_path),
                read_extensions=self.options.extensions,
            )
            reader = None
            try:
                reader = FileReader(opts)
            except errors.ValidationError as err:
                collector.handle(err)

            if reader is None:
                print(self.txt_crash("FATAL"), "Unable to initialize schema")
                exit()

            test("Schema definitions can be loaded", lambda: None)

            types = TypeMapping(reader, collector)
            test("Schema types can be inferred", lambda: None)

            test(
                "Check observable type_id definitions",
                lambda: validate_observables(reader, collector=collector, types=types),
            )

            # Validate dependencies
            test(
                "Dependency targets are resolvable and exist",
                lambda: validate_include_targets(
                    reader, collector=collector, types=types
                ),
            )

            process_includes(reader, collector=collector, types=types)

            # Any errors since the last test were duplicates; ignore them
            collector.flush()

            # Validate keys
            test(
                "Required keys are present",
                lambda: validate_required_keys(
                    reader, collector=collector, types=types
                ),
            )

            test(
                "There are no unrecognized keys",
                lambda: validate_no_unknown_keys(
                    reader, collector=collector, types=types
                ),
            )

            test(
                "All attributes in the dictionary are used",
                lambda: validate_unused_attrs(reader, collector=collector, types=types),
            )

            test(
                "All attributes are defined in dictionary.json",
                lambda: validate_undefined_attrs(
                    reader, collector=collector, types=types
                ),
            )

            test(
                "Names are not used multiple times within a record type",
                lambda: validate_intra_type_collisions(
                    reader, collector=collector, types=types
                ),
            )

            test(
                "Attribute type references are defined",
                lambda: validate_attr_types(reader, collector=collector, types=types),
            )

            test(
                "JSON files match their metaschema definitions",
                lambda: validate_metaschemas(reader, collector=collector, types=types),
            )

        except Exception as err:
            print("Encountered an unexpected exception:")
            traceback.print_exception(err)

        finally:
            print("")
            print(self.txt_emphasize("SUMMARY"))

            failure_threshold = (
                Severity.ERROR if not self.options.strict else Severity.WARN
            )

            for k in messages:
                found = False
                if len(messages[k].items()) > 0:
                    for sev in [
                        Severity.FATAL,
                        Severity.ERROR,
                        Severity.WARN,
                        Severity.INFO,
                    ]:
                        if sev in messages[k] and sev >= failure_threshold:
                            found = True
                            print("  ", self.txt_fail("FAILED") + ":", k)
                            exit_code = 1

                if not found:
                    print("  ", self.txt_pass("PASSED") + ":", k)

            print("")
            exit(exit_code)
