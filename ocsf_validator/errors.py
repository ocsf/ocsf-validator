from typing import Optional


class ValidationError(Exception):
    """Base class for validation errors."""

    ...


class InvalidBasePathError(ValidationError):
    ...


class InvalidMetaSchemaError(ValidationError):
    ...


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


class MissingDependencyError(Exception):
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
