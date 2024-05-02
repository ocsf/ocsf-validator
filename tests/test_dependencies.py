import pytest
from typing import Any

from ocsf_validator.errors import *
from ocsf_validator.processor import *
from ocsf_validator.reader import DictReader, Reader


def attributes(attrs: list = []) -> dict[str, Any]:
    d = {}
    for a in attrs:
        d[a] = {"name": a}
    return {"attributes": d}


def obj(name: str = "object", attrs: list = []) -> dict[str, Any]:
    return {"name": name, "caption": ""} | attributes(attrs)


def event(name: str = "event", attrs: list = []) -> dict[str, Any]:
    return {"name": name, "caption": ""} | attributes(attrs)


def test_include_one():
    net = attributes(["proxy", "src_ip"])
    net["name"] = "network"
    net["name2"] = "network"
    httpa = event("http_activity")
    httpa["$include"] = "includes/network.json"

    s = {
        "/events/network/http_activity.json": httpa,
        "/includes/network.json": net,
        "/dictionary.json": attributes(["stuff"]),
    }

    r = DictReader()
    r.set_data(s)
    process_includes(r)

    assert "attributes" in r["/events/network/http_activity.json"]
    assert "name2" in r["/events/network/http_activity.json"]
    assert r["/events/network/http_activity.json"]["name"] == "http_activity"
    assert "proxy" in r["/events/network/http_activity.json"]["attributes"]


def test_include_many():
    net = attributes(["proxy", "src_ip"])
    thing = attributes(["dest_ip", "score"])
    httpa = event("http_activity")
    httpa["$include"] = ["includes/network.json", "events/thing.json"]

    s = {
        "/events/network/http_activity.json": httpa,
        "/includes/network.json": net,
        "/events/thing.json": thing,
        "/dictionary.json": attributes(["stuff"]),
    }

    r = DictReader()
    r.set_data(s)
    process_includes(r)

    assert "attributes" in r["/events/network/http_activity.json"]
    assert r["/events/network/http_activity.json"]["name"] == "http_activity"
    assert "proxy" in r["/events/network/http_activity.json"]["attributes"]
    assert "dest_ip" in r["/events/network/http_activity.json"]["attributes"]


def test_include_attrs():
    net = attributes(["proxy", "src_ip"])
    thing = attributes(["dest_ip", "score"])
    httpa = event("http_activity")
    httpa["attributes"]["$include"] = ["includes/network.json", "events/thing.json"]

    s = {
        "/events/network/http_activity.json": httpa,
        "/includes/network.json": net,
        "/events/thing.json": thing,
        "/dictionary.json": attributes(["stuff"]),
    }

    r = DictReader()
    r.set_data(s)
    process_includes(r)

    assert "attributes" in r["/events/network/http_activity.json"]
    assert r["/events/network/http_activity.json"]["name"] == "http_activity"
    assert "proxy" in r["/events/network/http_activity.json"]["attributes"]
    assert "dest_ip" in r["/events/network/http_activity.json"]["attributes"]


def test_missing_include():
    httpa = event("http_activity")
    httpa["attributes"]["$include"] = "includes/network.json"

    s = {
        "/events/network/http_activity.json": httpa,
        "/dictionary.json": attributes(["stuff"]),
    }

    r = DictReader()
    r.set_data(s)

    with pytest.raises(MissingIncludeError):
        process_includes(r)


def test_extends():
    base = event("base_event", ["thing"])
    httpa = event("http_activity")
    httpa["extends"] = "base_event"

    s = {
        "/events/network/http_activity.json": httpa,
        "/events/base_event.json": base,
        "/dictionary.json": attributes(["stuff"]),
    }
    r = DictReader()
    r.set_data(s)

    process_includes(r)

    assert "thing" in r["/events/network/http_activity.json"]["attributes"]


def test_profiles_basic():
    prof = event("profile1", ["thing"])
    httpa = event("http_activity")
    httpa["profiles"] = "profile1"

    s = {
        "/events/network/http_activity.json": httpa,
        "/profiles/profile1.json": prof,
        "/dictionary.json": attributes(["stuff"]),
    }
    r = DictReader()
    r.set_data(s)

    process_includes(r)

    assert "thing" in r["/events/network/http_activity.json"]["attributes"]


def test_profiles_many():
    prof1 = event("profile1", ["thing1"])
    prof2 = event("profile2", ["thing2"])
    httpa = event("http_activity")
    httpa["profiles"] = ["profile1", "profile2"]

    s = {
        "/events/network/http_activity.json": httpa,
        "/profiles/profile1.json": prof1,
        "/profiles/profile2.json": prof2,
        "/dictionary.json": attributes(["stuff"]),
    }
    r = DictReader()
    r.set_data(s)

    process_includes(r)

    assert "thing1" in r["/events/network/http_activity.json"]["attributes"]
    assert "thing2" in r["/events/network/http_activity.json"]["attributes"]


def test_profiles():
    prof = event("profile1", ["thing"])
    prof["meta"] = "stuff"
    httpa = event("http_activity")
    httpa["profiles"] = "profile1"
    prof2 = event("profile1", ["thing2"])
    neta = event("network_activity")
    neta["profiles"] = "profile1"

    s = {
        "/extensions/one/events/network/http_activity.json": httpa,
        "/extensions/one/profiles/profile1.json": prof,
        "/events/network/net_activity.json": neta,
        "/profiles/profile1.json": prof2,
        "/dictionary.json": attributes(["stuff"]),
    }
    r = DictReader()
    r.set_data(s)

    process_includes(r)

    assert (
        "thing" in r["/extensions/one/events/network/http_activity.json"]["attributes"]
    )
    assert "meta" not in r["/extensions/one/events/network/http_activity.json"]
    assert (
        "thing2"
        not in r["/extensions/one/events/network/http_activity.json"]["attributes"]
    )
    assert "thing" not in r["/events/network/net_activity.json"]["attributes"]
    assert "thing2" in r["/events/network/net_activity.json"]["attributes"]


def test_attrs_from_dictionary():
    o1 = obj("o1", ["thing"])
    o1["attributes"]["thing"]["name"] = "thing1"

    d = {
        "attributes": {
            "thing": {"name": "thing", "caption": "Thing", "requirement": "optional"},
            "thing2": {"name": "thing2"},
        }
    }

    s = {
        "/objects/o1.json": o1,
        "/dictionary.json": d,
    }
    r = DictReader()
    r.set_data(s)

    process_includes(r)
    assert "thing" in r["/objects/o1.json"]["attributes"]
    assert r["/objects/o1.json"]["attributes"]["thing"]["name"] is "thing1"
    assert "thing2" not in r["/objects/o1.json"]["attributes"]
    assert "requirement" in r["/objects/o1.json"]["attributes"]["thing"]
