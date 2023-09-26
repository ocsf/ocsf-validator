import pytest

from ocsf_validator.errors import *
from ocsf_validator.reader import DictReader
from ocsf_validator.validators import *

d1 = {
    "/extensions/ext1/extension.json": {
        "uid": 1,
        "name": "ext1",
        "path": "ext1",
        # "caption": "Extension One"
        "color": "blue",
    }
}


def test_required_keys():
    r = DictReader()
    r.set_data(d1)

    with pytest.raises(MissingRequiredKeyError):
        validate_required_keys(r)


def test_unknown_keys():
    r = DictReader()
    r.set_data(d1)

    with pytest.raises(UnknownKeyError):
        validate_no_unknown_keys(r)


def test_validate_includes():
    r = DictReader()
    r.set_data(
        {
            "/objects/thing.json": {
                "$include": "bogus-file",
            }
        }
    )
    with pytest.raises(MissingIncludeError):
        validate_includes(r)


def test_validate_extends():
    r = DictReader()
    r.set_data({"/objects/thing.json": {"extends": "doesnt exist"}})
    with pytest.raises(MissingBaseError):
        validate_inheritance(r)


def test_validate_profiles():
    r = DictReader()
    r.set_data({"/objects/thing.json": {"profiles": "nah"}})
    with pytest.raises(MissingProfileError):
        validate_profiles(r)

def test_validate_unused_attrs():
    r = DictReader()
    r.set_data({
        "/dictionary.json": {
            "attributes": {
                "one": {
                    "name": "one",
                    "caption": "One",
                },
                "two": {
                    "name": "two",
                    "caption": "Two",
                },
                "three": {
                    "name": "three",
                    "caption": "Three",
                },
            },
        },
        "/objects/thing.json": {
            "name": "thing",
            "attributes": {
                "one": { "name": "one" },
            },
        },
        "/events/stuff/another-thing.json": {
            "name": "thing",
            "attributes": {
                "two": { "name": "two" },
            },
        }
    })

    with pytest.raises(UnusedAttributeError) as exc:
        validate_unused_attrs(r)
    assert exc.value.attr == "three"
