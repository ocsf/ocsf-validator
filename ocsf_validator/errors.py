from typing import Optional, TypeVar

TCollector = TypeVar("TCollector", bound="Collector")


class Collector:
    default: TCollector

    def __init__(self, throw: bool = True):
        self._exceptions: list[Exception] = []
        self._throw = throw

    def handle(self, err: Exception):
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


Collector.default = Collector()


class ValidationError(Exception):
    """Base class for validation errors."""

    ...


class InvalidBasePathError(ValidationError):
    ...


class InvalidMetaSchemaError(ValidationError):
    ...

class UnusedAttributeError(ValidationError):
    def __init__(self, attr: str):
        self.attr = attr
        super().__init__(f"Unused attribute {attr}")

class MissingRequiredKeyError(ValidationError):
    def __init__(self, key: str, file: str):
        self.key = key
        self.file = file
        super().__init__(f"Missing required key '{key}' in {file}")


class UnknownKeyError(ValidationError):
    def __init__(self, key: str, file: str):
        self.key = key
        self.file = file
        super().__init__(f"Unrecognized key '{key}' in {file}")


class MissingDependencyError(ValidationError):
    def __init__(self, file: str, include: str, message: Optional[str] = None):
        self.file = file
        self.include = include
        super().__init__(message)


class MissingIncludeError(MissingDependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(file, include, f"Missing include target '{include}' in {file}")


class MissingBaseError(MissingDependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(file, include, f"Missing base record '{include}' in {file}")


class MissingProfileError(MissingDependencyError):
    def __init__(self, file: str, include: str):
        self.file = file
        self.include = include
        super().__init__(file, include, f"Missing profile '{include}' in {file}")
