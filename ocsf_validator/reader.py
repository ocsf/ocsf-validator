"""Tools for working with OCSF schema definition files.

This module contains tools to work with the JSON files that define the OCSF
schema. The most important export is the `Reader` class, which allows convenient
access to the OCSF schema as its represented in the definition files.
"""

import json
import re
from abc import ABC
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path, PurePath
from typing import Any, Callable, Dict, Iterable, Optional

from ocsf_validator.errors import InvalidBasePathError
from ocsf_validator.matchers import Matcher
from ocsf_validator.types import *

# TODO would os.PathLike be better?
Pathable = str | Path

# TODO refine Any in type signature
SchemaData = Dict[str, Any]

Pattern = str | Matcher


@dataclass
class ReaderOptions:
    """Options to control the behavior of a Reader."""

    base_path: Optional[Path] = None
    """The base path from which to load the schema."""

    read_extensions: bool = True
    """Recurse extensions."""


class Reader(ABC):
    """An in-memory copy of the raw OCSF schema definition.

    The `Reader` maintains a dictionary with relative file paths as strings
    and values of `Map[str, Any]` that are the decoded JSON of each schema
    file.

    Args:
        options (str | Path):    a base path for the schema, probably a clone of
                                 the `ocsf-schema` repository.
        options (ReaderOptions): an instances of ReaderOptions to change
                                 behaviors of the Reader.
    """

    def __init__(self, options: ReaderOptions | Pathable | None = None) -> None:
        if options is not None:
            if not isinstance(options, ReaderOptions):
                if isinstance(options, str):
                    path = Path(options)
                else:
                    path = options
                options = ReaderOptions(base_path=path)

            self._options = options
        else:
            self._options = ReaderOptions()

        self._data: SchemaData = {}
        self._root: str = ""

    @property
    def base_path(self):
        return self._options.base_path

    def contents(self, path: Pathable) -> SchemaData:
        """Retrieve the parsed JSON data in a given file."""
        if isinstance(path, Path):
            path = str(path)

        # Can raise KeyError
        return self.__getitem__(path)

    def key(self, *args: str) -> str:
        """Platform agnostic key / filename creation from individual parts."""
        return str(self._root / Path(*args))

    def __getitem__(self, key: str):
        return self._data[key]

    def find(self, *parts: str) -> SchemaData | None:
        try:
            return self.__getitem__(self.key(*parts))
        except KeyError:
            return None

    def __setitem__(self, key: str, val: SchemaData):
        self._data[key] = val

    def __contains__(self, key: str):
        return key in self._data

    def __len__(self):
        return len(self._data)

    def ls(self, path: str | None = None, dirs=True, files=True) -> list[str]:
        if path is None:
            path = "/"
        if path[0] != "/":
            path = "/" + path

        base = Path(path)

        matched = set()
        for k in self._data.keys():
            p = Path(k)
            if p.parts[0 : len(base.parts)] == base.parts:
                depth = len(base.parts) + 1
                if (len(p.parts) == depth and files) or (len(p.parts) > depth and dirs):
                    matched.add(p.parts[len(base.parts)])

        return list(matched)

    def match(self, pattern: Optional[Pattern] = None) -> Iterable[str]:
        """Return a list of keys that match pattern."""
        if pattern is not None:
            pattern = Matcher.make(pattern)

        for k in self._data.keys():
            if pattern is None or pattern.match(k):
                yield k

    def apply(self, op: Callable, pattern: Optional[Pattern] = None) -> None:
        """Apply a function to every 'file' in the schema, optionally if it
        matches a globbing expression `target`."""

        for k in self.match(pattern):
            op(self, k)

    def map(
        self,
        op: Callable,
        pattern: Optional[Pattern] = None,
        accumulator: Any = None,
    ) -> Any:
        """Apply a function to every 'file' in the schema, optionally if it
        matches a globbing expression `target`, and return the accumulated
        result."""

        for k in self.match(pattern):
            accumulator = op(self, k, accumulator)

        return accumulator


class DictReader(Reader):
    """A Reader that works from a `dict` without reading the filesystem.

    Useful (hopefully) for testing and debugging."""

    def set_data(self, data: SchemaData):
        self._data = data.copy()
        self._root = Path(next(iter(self._data.keys()))).root


class FileReader(Reader):
    """A Reader that reads schema definitions from JSON files."""

    def __init__(self, options: ReaderOptions | Pathable | None) -> None:
        if options is None:
            raise InvalidBasePathError("No base path specified")

        super().__init__(options)

        path = self._options.base_path

        if path is None:
            raise InvalidBasePathError(
                f"Missing schema base path in constructor arguments."
            )

        if not path.is_dir():
            raise InvalidBasePathError(f'Schema base path "{path}" is not a directory.')

        self._root = path.root
        self._data = _walk(path, path, self._options)


TRAVERSABLE_PATHS = ["enums", "includes", "objects", "events", "profiles", "extensions"]


def _walk(path: Path, base: Path, options: ReaderOptions) -> SchemaData:
    data: SchemaData = {}

    for entry in path.iterdir():
        key = str(base.root / entry.relative_to(base))

        if entry.is_file() and entry.suffix == ".json":
            with open(entry) as file:
                try:
                    data[key] = json.load(file)
                except json.JSONDecodeError as e:
                    # TODO maybe reformat this error before raising it
                    raise e

        elif entry.is_dir() and (
            entry.name in TRAVERSABLE_PATHS or entry.parent.name in TRAVERSABLE_PATHS
        ):
            if entry.name == "extensions" and not options.read_extensions:
                break

            data |= _walk(entry, base, options)

    return data
