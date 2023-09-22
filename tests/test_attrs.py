import pytest

from ocsf_validator.processors import apply_attributes
from ocsf_validator.reader import DictReader


def reader():
    r = DictReader()
    data = {
        "/objects/thing.json": {
            "name": "thing",
            "attributes": {
                "size": {
                    "caption": "size",
                    "type": "int_t",
                },
                "color": {"name": "pigment"},
            },
        },
        "/dictionary.json": {
            "attributes": {
                "color": {"caption": "Color", "name": "color", "type": "string_t"},
                "unused": {
                    "name": "unused",
                },
            }
        },
    }
    r.set_data(data)
    return r


def test_key_from_parts():
    r = reader()
    k = r.key("dictionary.json")
    assert k == "/dictionary.json"


def test_merge():
    r = reader()
    apply_attributes(r)

    assert "size" in r["/objects/thing.json"]["attributes"]
    assert "color" in r["/objects/thing.json"]["attributes"]
    assert "unused" not in r["/objects/thing.json"]["attributes"]

    attr = r["/objects/thing.json"]["attributes"]["color"]
    assert attr["name"] == "pigment"
    assert attr["type"] == "string_t"
    assert attr["caption"] == "Color"
