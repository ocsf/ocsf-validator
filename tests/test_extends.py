import pytest

from ocsf_validator.errors import *
from ocsf_validator.processor import process_includes
from ocsf_validator.reader import DictReader


def reader():
    r = DictReader()
    data = {
        "/objects/thing1.json": {
            "name": "thing1",
            "caption": "Thing 1",
            "extends": "base",
        },
        "/objects/base.json": {
            "name": "base",
            "color": "blue",
        },
    }
    r.set_data(data)
    return r


def test_extends():
    r = reader()
    process_includes(r)

    d = r["/objects/thing1.json"]
    assert "name" in d
    assert "caption" in d
    assert "color" in d
    assert d["name"] == "thing1"
