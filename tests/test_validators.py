import pytest

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


def test_validate_attr_keys():
    r = DictReader()
    r.set_data(
        {
            "/objects/thing.json": {
                "name": "thing",
                "attributes": {
                    "one": {"name": "one", "type": "string_t"},
                    "two": {"name": "two", "type": "thing2"},
                },
            },
            "/objects/thing2.json": {
                "name": "thing2",
                "attributes": {},
            },
            "/objects/dictionary.json": {
                "types": {
                    "attributes": {
                        "string_t": {},
                    },
                },
            },
        }
    )

    # raise no errors
    validate_attr_types(r)

    r["/objects/thing2.json"]["name"] = "thing3"
    with pytest.raises(InvalidAttributeTypeError):
        validate_attr_types(r)


def test_validate_observables():
    good_data = {
        "dictionary.json": {
            "attributes": {
                "name": {"caption": "Name", "type": "string_t"},
                "alpha": {"caption": "Alpha", "type": "string_t"},
                "beta": {"caption": "Beta", "type": "string_t"},
                "gamma": {"caption": "Gamma", "type": "gamma_t", "observable": 1},
                "delta": {"caption": "Delta", "type": "delta_t"},
            },
            "types": {
                "attributes": {
                    "string_t": {"caption": "String"},
                    "integer_t": {"caption": "Integer"},
                    "gamma_t": {"caption": "Gamma_T", "type": "string_t", "type_name": "String"},
                    "delta_t": {"caption": "Delta_T", "type": "integer_t", "type_name": "Integer", "observable": 2},
                },
            }
        },

        "/objects/bird.json": {
            "name": "bird",
            "caption": "Bird",
            "attributes": {
                "name": {"requirement": "required"},
                "alpha": {"requirement": "required"},
            }
        },
        "/objects/cat.json": {
            "name": "cat",
            "caption": "Cat",
            "observable": 10,
            "attributes": {
                "name": {"requirement": "required"},
                "alpha": {"requirement": "required"}
            }
        },
        "/objects/dog.json": {
            "name": "dog",
            "caption": "Dog",
            "attributes": {
                "name": {"requirement": "required"},
                "alpha": {"requirement": "required", "observable": 11},
            }
        },
        "/objects/dog_house.json": {
            "name": "dog_house",
            "caption": "Dog House",
            "attributes": {
                "tenant": {"type": "dog", "requirement": "required"}
            },
            "observables": {
                "dog.name": 12
            }
        },

        "/events/blue.json": {
            "uid": 1,
            "name": "blue",
            "caption": "Blue",
        },
        "/events/green.json": {
            "uid": 2,
            "name": "green",
            "caption": "Green",
            "observable": 100,
        },
        "/events/red.json": {
            "uid": 3,
            "name": "red",
            "caption": "Red",
            "attributes": {
                "beta": {"requirement": "required", "observable": 101}
            }
        },
        "/events/yellow.json": {
            "uid": 4,
            "name": "yellow",
            "caption": "Yellow",
            "attributes": {
                "bird": {"requirement": "required"}
            },
            "observables": {
                "bird.name": 102
            }
        },
    }

    observables = validate_and_get_observables(DictReader(good_data))
    assert observables is not None
    assert len(observables) == 7
    print("\ntest_validate_observables - collected observables:")
    print(observables_to_string(observables))

    with pytest.raises(IllegalObservableTypeIDError):
        bad_data = dict(good_data)
        bad_data["/objects/_hidden.json"] = {"name": "_hidden", "caption": "Hidden", "observable": 1}
        validate_observables(DictReader(bad_data))

    with pytest.raises(IllegalObservableTypeIDError):
        bad_data = dict(good_data)
        bad_data["/objects/_hidden.json"] = {
            "name": "_hidden",
            "caption": "Hidden",
            "attributes": {
                "beta": {"requirement": "required", "observable": 1}
            }
        }
        validate_observables(DictReader(bad_data))

    with pytest.raises(IllegalObservableTypeIDError):
        bad_data = dict(good_data)
        bad_data["/events/_hidden.json"] = {
            "name": "hidden",
            "caption": "Hidden",
            "attributes": {
                "beta": {"requirement": "required", "observable": 1}
            }
        }
        validate_observables(DictReader(bad_data))

    with pytest.raises(ObservableTypeIDCollisionError):
        bad_data = dict(good_data)
        dictionary_attributes = bad_data["dictionary.json"]["attributes"]
        dictionary_attributes["epsilon"] = {"caption": "Epsilon", "type": "string_t", "observable": 1}
        validate_observables(DictReader(bad_data))

    with pytest.raises(ObservableTypeIDCollisionError):
        bad_data = dict(good_data)
        dictionary_types_attributes = bad_data["dictionary.json"]["types"]["attributes"]
        dictionary_types_attributes["epsilon_t"] = {
            "caption": "Epsilon_T", "type": "string_t", "type_name": "String", "observable": 2
        },
        validate_observables(DictReader(bad_data))


def test_validate_event_categories():
    good_data = {
        "categories.json": {
            "attributes": {
                "alpha": {"caption": "Alpha", "uid": 1},
                "beta": {"caption": "Beta", "uid": 2},
            }
        },
        "events/foo.json": {"caption": "Foo", "category": "alpha"},
        "events/bar.json": {"caption": "Bar", "category": "beta"},
        "events/baz.json": {"caption": "Baz", "category": "other"},
        "events/guux.json": {"caption": "Quux"},
    }
    validate_event_categories(DictReader(good_data))


def test_validate_metaschemas():
    # set up a json schema that expects an object with a name property only
    object_json_schema = {
        "$id": "https://schema.ocsf.io/object.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Object",
        "type": "object",
        "required": [
            "name"
        ],
        "properties": {
            "name": {
                "type": "string"
            }
        },
        "additionalProperties": False
    }

    # set up a function to a create a registry in memory
    expected_schemas = [
        "object.schema.json",
        "event.schema.json"
    ]

    def _get_registry(reader, base_uri):
        registry = referencing.Registry()
        for schema in expected_schemas:
            resource = referencing.Resource.from_contents(object_json_schema)
            registry = registry.with_resource(base_uri + schema, resource=resource)
        return registry

    # test that a bad schema fails validation
    r = DictReader()
    r.set_data(
        {
            "/objects/thing.json": {
                "notARealAttribute": "thing",
            },
        }
    )

    with pytest.raises(InvalidMetaSchemaError) as exc:
        validate_metaschemas(r, get_registry=_get_registry)

    # test that a good schema passes validation
    r = DictReader()
    r.set_data(
        {
            "/objects/thing.json": {
                "name": "thing",
            },
        }
    )

    validate_metaschemas(r, get_registry=_get_registry)

    # test that a good schema passes validation
    r = DictReader()
    r.set_data(
        {
            "/objects/thing.json": {
                "name": "thing",
            },
        }
    )

    validate_metaschemas(r, get_registry=_get_registry)

    # test that a missing metaschema file fails validation
    def _get_blank_registry(reader, base_uri):
        registry = referencing.Registry()
        return registry

    with pytest.raises(InvalidMetaSchemaFileError) as exc:
        validate_metaschemas(r, get_registry=_get_blank_registry)
