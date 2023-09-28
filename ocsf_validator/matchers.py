import re
from abc import ABC
from pathlib import Path

from ocsf_validator.types import *


class Matcher:
    def match(self, value: str):
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
