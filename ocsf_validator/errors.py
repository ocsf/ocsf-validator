from typing import Iterable, Optional, TypeVar

TCollector = TypeVar("TCollector", bound="Collector")


class Collector:
    """An error collector used by schema operations so that encountered errors
    can be saved for later and displayed as test output.

    The default behavior is to `raise` all exceptions, so you shouldn't
    notice the collector until `throw` is `False`.
    """

    default: TCollector  # type: ignore
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


class InvalidBasePathError(ValidationError):
    ...


class InvalidMetaSchemaError(ValidationError):
    ...


class InvalidMetaSchemaFileError(ValidationError):
    ...


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

        if cls is None:
            cls_str = ""
        else:
            cls_str = cls.__name__ + "."

        super().__init__(
            f"Missing required key `{cls_str}{key}` at `{trail_str}` in {file}"
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

        if cls is None:
            cls_str = ""
        else:
            cls_str = cls.__name__

        super().__init__(
            f"Unrecognized key `{key}` of `{cls_str}` at `{trail_str}` in {file}"
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
            self.cls = t
        else:
            self.cls: str = t.__name__
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
            f" in file {file} and {', '.join(other_defs)}"
        )
