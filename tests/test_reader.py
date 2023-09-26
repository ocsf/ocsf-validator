from pathlib import Path

import pytest

from ocsf_validator.matchers import GlobMatcher
from ocsf_validator.reader import DictReader, Reader


event = {"name": "an event"}
obj = {"name": "an object"}
data = {
    "/events/base_event.json": event.copy(),
    "/events/application/application.json": event.copy(),
    "/objects/os.json": obj.copy(),
    "/extensions/win/objects/win_process.json": obj.copy(),
    "/extensions/win/events/system/registry_key.json": event.copy(),
}


def reader():
    r = DictReader()
    r.set_data(data)
    return r


def test_get_item():
    r = reader()
    assert r["/objects/os.json"] == obj
    assert r.contents("/objects/os.json") == obj


def test_set_item():
    r = reader()
    r["/objects/api.json"] = {"name": "api"}
    assert r["/objects/api.json"]["name"] == "api"


def test_apply():
    r = reader()

    def mark(reader: Reader, key: str):
        reader[key]["test"] = True

    r.apply(mark, GlobMatcher("objects/*"))
    assert r["/objects/os.json"]["test"] == True
    assert r["/extensions/win/objects/win_process.json"]["test"] == True


def test_find():
    r = reader()
    f = r.find("objects", "os.json")
    assert "name" in f


def test_map():
    r = reader()

    def f(reader: Reader, key: str, acc: int):
        return acc + 1

    matches = r.map(f, GlobMatcher("objects/*"), 0)
    assert matches == 2


def test_ls():
    r = reader()

    matches = r.ls()
    assert "objects" in matches
    assert "win" not in matches

    matches = r.ls("objects")
    assert "os.json" in matches
    assert "win" not in matches

    matches = r.ls("extensions")
    assert "os.json" not in matches
    assert "win" in matches

    matches = r.ls("events", files=False)
    assert "application" in matches
    assert "base_event.json" not in matches

    matches = r.ls("events", dirs=False)
    assert "application" not in matches
    assert "base_event.json" in matches


def test_extension():
    r = reader()

    assert r.extension("/extensions/win/objects/os.json") == "win"
    assert r.extension("/objects/os.json") is None
    assert r.extension("extensions/windows/events/registry_key.json") == "windows"
