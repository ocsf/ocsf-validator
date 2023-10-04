import re
from abc import ABC
from pathlib import Path
from typing import Optional

from ocsf_validator.types import *


class Matcher:
    def match(self, value: str) -> bool:
        raise NotImplementedError()

    @staticmethod
    def make(pattern):
        if isinstance(pattern, Matcher):
            return pattern
        else:
            return RegexMatcher(pattern)


class TypeMatcher:
    def get_type(self) -> type:
        raise NotImplementedError()


class AnyMatcher(Matcher):
    def __init__(self, matchers: Optional[list[Matcher]] = None):
        if matchers is not None:
            self._matchers = matchers
        else:
            self._matchers = []

    def match(self, value: str):
        for matcher in self._matchers:
            if matcher.match(value):
                return True

    def add(self, matcher: Matcher):
        self._matchers.append(matcher)


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


class DictionaryMatcher(RegexMatcher, TypeMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*dictionary.json")

    def get_type(self):
        return OcsfDictionary


class VersionMatcher(RegexMatcher, TypeMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*version.json")

    def get_type(self):
        return OcsfVersion


class ObjectMatcher(RegexMatcher, TypeMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*objects/.*json")

    def get_type(self):
        return OcsfObject


class EventMatcher(RegexMatcher, TypeMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*events/.*json")

    def get_type(self):
        return OcsfEvent


class ExtensionMatcher(GlobMatcher, TypeMatcher):
    def __init__(self):
        self._pattern = "extensions/*/extension.json"

    def get_type(self):
        return OcsfExtension


class IncludeMatcher(RegexMatcher, TypeMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*includes/.*.json")

    def get_type(self):
        return OcsfInclude


class ProfileMatcher(RegexMatcher, TypeMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*profiles/.*.json")

    def get_type(self):
        return OcsfProfile


class CategoriesMatcher(RegexMatcher, TypeMatcher):
    def __init__(self):
        self._pattern = re.compile(r".*categories.json")

    def get_type(self):
        return OcsfCategories
