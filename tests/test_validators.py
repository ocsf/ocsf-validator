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


def test_deep_required_keys():
    s = {
        "/events/event.json": {
            "caption": "Event",
            "name": "event",
            "attributes": {
                "one": {
                    "name": "one",
                },
            },
        },
    }
    r = DictReader()
    r.set_data(s)

    with pytest.raises(MissingRequiredKeyError) as exc:
        validate_required_keys(r)
    assert exc.value.key is "caption"


def test_unknown_keys():
    r = DictReader()
    r.set_data(d1)

    with pytest.raises(UnknownKeyError):
        validate_no_unknown_keys(r)


def test_validate_unused_attrs():
    r = DictReader()
    r.set_data(
        {
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
                    "one": {"name": "one"},
                },
            },
            "/events/stuff/another-thing.json": {
                "name": "thing",
                "attributes": {
                    "two": {"name": "two"},
                },
            },
        }
    )

    with pytest.raises(UnusedAttributeError) as exc:
        validate_unused_attrs(r)
    assert exc.value.attr == "three"


def test_validate_undefined_attrs():
    r = DictReader()
    r.set_data(
        {
            "/dictionary.json": {
                "attributes": {
                    "one": {
                        "name": "one",
                        "caption": "One",
                    },
                },
            },
            "/objects/thing.json": {
                "name": "thing",
                "attributes": {
                    "one": {"name": "one"},
                    "two": {"name": "two"},
                },
            },
        }
    )

    with pytest.raises(UndefinedAttributeError) as exc:
        validate_undefined_attrs(r)
    assert exc.value.attr == "two"


def test_validate_intra_type_collisions():
    r = DictReader()
    r.set_data(
        {
            "/objects/thing.json": {
                "name": "thing",
                "attributes": {
                    "one": {"name": "one"},
                    "two": {"name": "two"},
                },
            },
            "/objects/thing2.json": {
                "name": "thing",
                "attributes": {},
            },
        }
    )

    with pytest.raises(TypeNameCollisionError) as exc:
        validate_intra_type_collisions(r)
    assert exc.value.name == "thing"

    r["/events/event.json"] = {"name": "thing"}
    r["/objects/thing2.json"] = {"name": "thing2"}
    # no error
    validate_intra_type_collisions(r)


def test_validate_metaschemas():
    # TODO
    pytest.fail()