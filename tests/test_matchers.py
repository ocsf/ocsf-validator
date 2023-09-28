import pytest

from ocsf_validator.matchers import *
from ocsf_validator.types import *


def test_dictionary_matcher():
    m = DictionaryMatcher()

    assert m.match("dictionary.json") is True
    assert m.match("/dictionary.json") is True
    assert m.match("/extension/win/dictionary.json") is True
    assert m.match("/objects/thing.json") is False
    assert m.get_type() is OcsfDictionary


def test_object_matcher():
    m = ObjectMatcher()

    assert m.match("/objects/thing.json") is True
    assert m.match("/extensions/win/objects/thing.json") is True
    assert m.match("objects/win/objects/thing.json") is True
    assert m.match("/events/thing.json") is False
    assert m.get_type() is OcsfObject


def test_event_matcher():
    m = EventMatcher()

    assert m.match("/events/base_event.json") is True
    assert m.match("events/activity/network_activity.json") is True
    assert m.match("events/filesystem/filesystem.json") is True
    assert m.match("/extensions/win/events/activity/network_activity.json") is True
    assert m.get_type() is OcsfEvent


def test_extension_matcher():
    m = ExtensionMatcher()

    assert m.match("/extensions/ext1/extension.json") is True
    assert m.match("/extension.json") is False
    assert m.get_type() is OcsfExtension


def test_make_matcher():
    m = Matcher.make(".*thing.json")

    assert m.match("thing.json") is True
