
import re
from abc import ABC
from pathlib import Path

class Matcher:
    def match(self, value: str):
        raise NotImplementedError()

    @staticmethod
    def make(pattern):
        if isinstance(pattern, Matcher):
            return pattern
        else:
            return RegexMatcher(pattern)


class RegexMatcher(Matcher):
    def __init__(self, pattern: str | re.Pattern):
        if isinstance(pattern, str):
            self._pattern = re.compile(pattern)
        else:
            self._pattern = pattern

    def match(self, value: str):
        return self._pattern.match(value) is not None

class GlobMatcher(Matcher):
    def __init__(self, pattern: str):
        self._pattern = pattern

    def match(self, value: str):
        path = Path(value)
        return path.match(self._pattern)

class DictionaryMatcher(RegexMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*dictionary.json")

class ObjectMatcher(RegexMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*/objects/.*json")

class EventMatcher(RegexMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*/events/.*json")

class ExtensionMatcher(GlobMatcher):
    def __init__(self):
        self._pattern = "extensions/*/extension.json"
