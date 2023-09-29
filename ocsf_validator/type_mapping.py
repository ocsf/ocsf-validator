from pathlib import Path

from ocsf_validator.errors import Collector, UndetectableTypeError
from ocsf_validator.matchers import *
from ocsf_validator.reader import Reader
from ocsf_validator.types import *

MATCHERS = [
    VersionMatcher(),
    DictionaryMatcher(),
    CategoriesMatcher(),
    IncludeMatcher(),
    CategoriesMatcher(),
    ProfileMatcher(),
    ObjectMatcher(),
    EventMatcher(),
    ExtensionMatcher(),
]


class TypeMapping:
    def __init__(self, reader: Reader, collector: Collector = Collector.default):
        self._reader = reader
        self._collector = collector
        self._mappings: dict[str, type] = {}
        self.update()

    def __getitem__(self, path: str) -> type:
        return self._mappings[path]

    def __contains__(self, path: str) -> bool:
        return path in self._mappings

    def __iter__(self):
        return iter(self._mappings)

    def _get_type(self, path: str) -> type | None:
        for matcher in MATCHERS:
            if matcher.match(path):
                return matcher.get_type()
        return None

    def update(self):
        for path in self._reader.match():
            t = self._get_type(path)
            if t is not None:
                self._mappings[path] = t
            else:
                self._collector.handle(UndetectableTypeError(path))

    def extension(self, path: str) -> str | None:
        """Extract the extension name from a given key/filepath."""
        parts = list(Path(self._reader.key(path)).parts)
        if "extensions" in parts:
            return parts[parts.index("extensions") + 1]
        else:
            return None
