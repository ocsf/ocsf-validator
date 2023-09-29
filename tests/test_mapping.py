import pytest

from ocsf_validator.reader import DictReader
from ocsf_validator.type_mapping import *


def test_mapping():
    s = {
        "/dictionary.json": {},
        "/objects/object.json": {},
        "/categories.json": {},
        "/profiles/profile.json": {},
        "/version.json": {},
        "/events/event.json": {},
        "/extensions/a/events/event.json": {},
        "/extensions/a/objects/object.json": {},
        "/extensions/a/profiles/profile.json": {},
    }
    r = DictReader()
    r.set_data(s)
    tm = TypeMapping(r)

    assert tm["/dictionary.json"] is OcsfDictionary
    assert tm["/events/event.json"] is OcsfEvent
    assert tm["/extensions/a/events/event.json"] is OcsfEvent
    assert tm["/objects/object.json"] is OcsfObject
    assert tm["/extensions/a/objects/object.json"] is OcsfObject
    assert tm["/categories.json"] is OcsfCategories
    assert tm["/version.json"] is OcsfVersion
    assert tm["/profiles/profile.json"] is OcsfProfile
    assert tm["/extensions/a/profiles/profile.json"] is OcsfProfile
