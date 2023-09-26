
import pytest

from ocsf_validator.matchers import *


def test_dictionary_matcher():
    m = DictionaryMatcher()

    assert m.match("dictionary.json")
    assert m.match("/dictionary.json")
    assert m.match("/extension/win/dictionary.json")
    assert m.match("/objects/thing.json") is False

def test_object_matcher():
    m = ObjectMatcher()

    assert m.match("/objects/thing.json")
    assert m.match("/extensions/win/objects/thing.json")
    assert m.match("objects/win/objects/thing.json")
    assert m.match("/events/thing.json") is False

def test_event_matcher():
    m = EventMatcher()

    assert m.match("/events/base_event.json")
    assert m.match("/events/activity/network_activity.json")
    assert m.match("/extensions/win/events/activity/network_activity.json")

