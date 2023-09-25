import pytest

from ocsf_validator.processors import apply_profiles
from ocsf_validator.reader import DictReader


def reader():
    r = DictReader()
    data = {
        "/objects/thing1.json": {
            "name": "thing1",
            "caption": "Thing 1",
            "profiles": "/profiles/p1.json",
        },
        "/objects/thing2.json": {
            "name": "thing2",
            "profiles": ["/profiles/p2.json", "/profiles/p3.json"],
        },
        "/profiles/p1.json": {
            "name": "p1",
            "color": "blue",
            "attributes": {"one": 1},
        },
        "/profiles/p2.json": {
            "name": "p2",
            "speed": "fast",
            "color": "blue",
            "attributes": {"two": 2},
        },
        "/profiles/p3.json": {
            "name": "p3",
            "attributes": {"three": 3},
        },
        "/extensions/one/profiles/p4.json": {
            "name": "p4",
            "attributes": {"three": 4},
        },
        "/extensions/one/objects/thing3.json": {
            "name": "thing3",
            "profiles": ["profiles/p4"],
        },
    }
    r.set_data(data)
    return r


def test_profiles():
    r = reader()
    apply_profiles(r)

    d = r["/objects/thing1.json"]
    assert "name" in d
    assert "caption" in d
    assert "color" in d
    assert d["name"] == "thing1"


def test_many_profiles():
    r = reader()
    apply_profiles(r)

    d = r["/objects/thing2.json"]
    assert "two" in d["attributes"]
    assert "three" in d["attributes"]


def test_profiles_filter():
    r = reader()
    apply_profiles(r, ["/profiles/p3.json"])

    d = r["/objects/thing2.json"]
    assert "two" not in d["attributes"]
    assert "three" in d["attributes"]


def test_profiles_extn():
    r = reader()
    apply_profiles(r)

    d = r["/extensions/one/objects/thing3.json"]
    assert "three" in d["attributes"]
