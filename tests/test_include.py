import pytest

from ocsf_validator.processors import MissingIncludeError, apply_include
from ocsf_validator.reader import DictReader


def reader():
    r = DictReader()
    data = {
        "/events/network/http_activity.json": {
            "name": "http_activity",
            "$include": "includes/network.json",
        },
        "/events/auth/authentication.json": {
            "name": "authentication",
            "$include": ["includes/network.json", "includes/thing.json"],
        },
        "/events/network/dhcp.json": {
            "name": "dhcp_activity",
            "$include": "includes/thing2.json",
        },
        "/events/network/merge.json": {
            "$include": ["includes/thing.json", "includes/network.json"]
        },
        "/objects/wenum.json": {"attributes": {"numbers": {"$include": "enums/e.js"}}},
        "/includes/network.json": {
            "caption": "Network event stuff",
            "attributes": {"proxy": {"requirement": "optional"}},
        },
        "/includes/thing.json": {"attributes": {"color": {"type": "string_t"}}},
        "/includes/thing2.json": {"name": "thing2"},
        "/enums/e.js": {
            "enum": {
                "1": {
                    "caption": "one",
                },
                "2": {
                    "caption": "two",
                },
            }
        },
    }
    r.set_data(data)
    return r


def test_include():
    r = reader()
    apply_include(r)

    d = r["/events/network/http_activity.json"]
    assert "name" in d
    assert "caption" in d
    assert "attributes" in d
    assert d["attributes"]["proxy"]["requirement"] == "optional"


def test_include_many():
    r = reader()
    apply_include(r)

    d = r["/events/auth/authentication.json"]
    assert "name" in d
    assert "attributes" in d
    assert d["attributes"]["color"]["type"] == "string_t"


def test_apply_include():
    r = reader()
    apply_include(r)
    d = r["/events/network/http_activity.json"]
    assert "name" in d
    assert "caption" in d
    assert "attributes" in d
    assert d["attributes"]["proxy"]["requirement"] == "optional"


def test_include_merge_order():
    r = reader()
    apply_include(r)

    assert r["/events/network/dhcp.json"]["name"] == "dhcp_activity"


def test_include_deep_merge():
    r = reader()
    apply_include(r)

    subj = r["/events/network/merge.json"]
    assert "color" in subj["attributes"]
    assert "proxy" in subj["attributes"]


def test_include_missing():
    r = reader()
    r["/objects/bad-include.json"] = {"$include": "/not/really/here.json"}

    with pytest.raises(MissingIncludeError):
        apply_include(r)


def test_include_enum():
    r = reader()
    apply_include(r)

    subj = r["/objects/wenum.json"]
    assert "attributes" in subj
    assert "numbers" in subj["attributes"]
    assert "enum" in subj["attributes"]["numbers"]
    assert "1" in subj["attributes"]["numbers"]["enum"]


def test_include_extn():
    ...
