
import re
from abc import ABC
from pathlib import Path
from enum import IntEnum

class MatchMode(IntEnum):
    GLOB = 1
    REGEX = 2

class Matcher:
    def match(self, value: str):
        raise NotImplementedError()

class RegexMatcher(Matcher):
    def __init__(self, pattern: str | re.Pattern):
        if isinstance(pattern, str):
            self._pattern = re.compile(pattern)
        else:
            self._pattern = pattern

    def match(self, value: str):
        return self._pattern.match(value) is not None

class GlobMatcher(Matcher):
    def __init__(self, pattern: str | Path):
        if isinstance(pattern, str):
            self._pattern = Path(pattern)
        else:
            self._pattern = pattern

    def match(self, value: str):
        return self._pattern.match(value)

class DictionaryMatcher(RegexMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*dictionary.json")

class ObjectMatcher(RegexMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*/objects/.*json")

class EventMatcher(RegexMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*/events/.*json")
