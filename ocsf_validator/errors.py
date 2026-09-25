from __future__ import annotations

from typing import Any, Iterable, Optional


class Collector:
    """An error collector used by schema operations so that encountered errors
    can be saved for later and displayed as test output.

    The default behavior is to `raise` all exceptions, so you shouldn't
    notice the collector until `throw` is `False`.
    """

    default: Collector
    """Simple singleton used whenever an Optional[Collector] parameter is None."""

    def __init__(self, throw: bool = True):
        self._exceptions: list[Exception] = []
        self._throw = throw

    def handle(self, err: Exception):
        """Handle an exception.

        By default, exceptions are stored and raised. But if `throw` is `False`,
        exceptions will only be stored for later."""

        self._exceptions.append(err)
        if self._throw:
            raise err

    def exceptions(self):
        return self._exceptions

    def flush(self):
        e = list(self._exceptions)
        self._exceptions = []
        return e

    def __len__(self):
        return len(self._exceptions)

    def __iter__(self) -> Iterable[Exception]:
        return iter(self._exceptions)


Collector.default = Collector()


class ValidationError(Exception):
    """Base class for validation errors."""

    ...


class InvalidBasePathError(ValidationError): ...


class InvalidMetaSchemaError(ValidationError): ...


class InvalidMetaSchemaFileError(ValidationError): ...


class UnusedAttributeError(ValidationError):
    def __init__(self, attr: str):
        self.attr = attr
        super().__init__(f"Unused attribute {attr}")


class MissingRequiredKeyError(ValidationError):
    def __init__(
        self,
        key: str,
        file: str,
        cls: Optional[type] = None,
        trail: Optional[list[str]] = None,
    ):
        self.key = key
        self.file = file
        self.cls = cls
        self.trail = trail

        if trail is None:
            trail_str = ""
        else:
            trail_str = ".".join(trail)

        super().__init__(
            f"Missing required key `{key}` at `{trail_str}` in {file}.  Make sure required fields in this file and any supporting files such as dictionaries or includes are populated."
        )


class UnknownKeyError(ValidationError):
    def __init__(
        self,
        key: str,
        file: str,
        cls: Optional[type] = None,
        trail: Optional[list[str]] = None,
    ):
        self.key = key
        self.file = file
        self.cls = cls
        self.trail = trail

        if trail is None:
            trail_str = ""
        else:
            trail_str = ".".join(trail)

        super().__init__(
            f"Unrecognized key `{key}` at `{trail_str}` in {file}.  Make sure fields in this file and any supporting files such as dictionaries or includes are valid."
        )


class DependencyError(ValidationError):
    def __init__(self, file: str, include: str, message: Optional[str] = None):
        self.file = file
        self.include = include
        super().__init__(message)


class MissingIncludeError(DependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(file, include, f"Missing include target '{include}' in {file}")


class MissingBaseError(DependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(file, include, f"Missing base record '{include}' in {file}")


class ImpreciseBaseError(DependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(
            file,
            include,
            f"Possibly ambiguous base record definition '{include}' in {file}",
        )


class MissingProfileError(DependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(file, include, f"Missing profile '{include}' in {file}")


class SelfInheritanceError(DependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(file, include, f"Inheritance from self '{include}' in {file}")


class RedundantProfileIncludeError(DependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(
            file,
            include,
            f"Redundant $include and profiles entry '{include}' in {file}",
        )


class UndetectableTypeError(ValidationError):
    def __init__(self, file: str):
        self.file = file
        super().__init__(f"Unable to detect type of {file}")


class IncludeTypeMismatchError(ValidationError):
    def __init__(
        self, file: str, include: str, t: type | str, directive: str = "$include"
    ):
        self.file = file
        self.include = include
        if isinstance(t, str):
            self.cls: str = t
        else:
            self.cls = t.__name__
        self.directive = directive
        super().__init__(
            f"`{directive}` type mismatch in {file}: expected type `{self.cls}` for {include}"
        )


class TypeNameCollisionError(ValidationError):
    def __init__(self, name: str, kind: str, file1: str, file2: str):
        self.name = name
        self.kind = kind
        self.file1 = file1
        self.file2 = file2
        super().__init__(f"Name collision for `{name}` between {file1} and {file2}")


class UndefinedAttributeError(ValidationError):
    def __init__(self, attr: str, file: str):
        self.attr = attr
        self.file = file
        super().__init__(
            f"Attribute `{attr}` in {file} is not defined in any attribute"
        )


class InvalidAttributeTypeError(ValidationError):
    def __init__(self, ref: str, attr: str, file: str):
        super().__init__(f"Invalid type {ref} for {attr} in {file}")


class IllegalObservableTypeIDError(ValidationError):
    def __init__(self, cause: str):
        super().__init__(cause)


class ObservableTypeIDCollisionError(ValidationError):
    def __init__(self, type_id: int, this_def: str, other_defs: list[str], file: str):
        super().__init__(
            f"Collision with observable type_id {type_id} between {this_def}"
            f" in file {file} and {', '.join(other_defs)}."
        )


class UnknownCategoryError(ValidationError):
    def __init__(self, category: str, file: str):
        super().__init__(f'Unknown category "{category}" in "{file}"')


class ConstraintMemberError(ValidationError):
    """A constraint member does not satisfy the recommended-attribute rule."""

    def __init__(self, kind: str, member: str, file: str, message: str):
        self.kind = kind
        self.member = member
        self.file = file
        super().__init__(message)


class ConstraintMemberRequirementError(ConstraintMemberError):
    def __init__(self, kind: str, member: str, file: str, requirement: Optional[str]):
        shown = requirement if requirement is not None else "unset"
        super().__init__(
            kind,
            member,
            file,
            f'Constraint {kind} member "{member}" in {file} is {shown};'
            " attributes in a constraint must be recommended.",
        )


class ConstraintMemberMissingError(ConstraintMemberError):
    def __init__(self, kind: str, member: str, file: str):
        super().__init__(
            kind,
            member,
            file,
            f'Constraint {kind} member "{member}" in {file} is not an attribute'
            " of this record.",
        )


class ConstraintMemberRequiredError(ConstraintMemberError):
    def __init__(self, kind: str, member: str, file: str):
        super().__init__(
            kind,
            member,
            file,
            f'Constraint {kind} member "{member}" in {file} is required, which'
            " makes the constraint redundant. Constraint members must be"
            " recommended.",
        )


def _cycle_str(cycle: list[tuple[str, str]]) -> str:
    """Render a cycle as `record.attr -> record.attr -> record`."""
    return (
        " -> ".join(f"{record}.{attr}" for record, attr in cycle) + f" -> {cycle[0][0]}"
    )


class MissingRecursiveAnnotationError(ValidationError):
    def __init__(self, attr: str, file: str, cycle: list[tuple[str, str]]):
        self.attr = attr
        self.file = file
        self.cycle = cycle
        super().__init__(
            f"Attribute `{attr}` in {file} recurses ({_cycle_str(cycle)})"
            f" but is not marked with `@recursive`. Add the annotation so tools"
            f" walking the schema know to stop expanding this branch."
        )


class UnnecessaryRecursiveAnnotationError(ValidationError):
    def __init__(self, attr: str, file: str):
        self.attr = attr
        self.file = file
        super().__init__(
            f"Attribute `{attr}` in {file} is marked with `@recursive` but does"
            f" not recurse. Remove the annotation."
        )


class InvalidRecursionPathError(ValidationError):
    def __init__(
        self,
        attr: str,
        file: str,
        declared: Any,
        cycles: list[list[tuple[str, str]]],
    ):
        self.attr = attr
        self.file = file
        self.declared = declared
        self.cycles = cycles
        # `declared` is whatever the schema file held, so it may not be a
        # sequence of strings. Rendering it must not raise: this error is the
        # report that the value is wrong.
        if isinstance(declared, (list, tuple)):
            shown = "[" + ", ".join(repr(entry) for entry in declared) + "]"
        else:
            shown = repr(declared)
        expected = "; ".join(
            " -> ".join(f"{record}.{a}" for record, a in cycle[1:]) or "(none)"
            for cycle in cycles
        )
        super().__init__(
            f"Attribute `{attr}` in {file} declares `@recursive.path` {shown},"
            f" which does not describe a chain of attributes leading from its"
            f" type back to `{cycles[0][0] if cycles else attr}`."
            f" Shortest closing chain: {expected}."
        )
