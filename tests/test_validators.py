from copy import deepcopy

import pytest

from ocsf_validator.reader import DictReader, ReaderOptions
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


def _recursion_reader(annotation=None, manager_annotation=None):
    """A schema with one direct cycle (thing.self_ref) and one two-hop cycle
    (person.manager -> user.person), plus a non-recursive attribute."""
    return DictReader(
        {
            "/objects/thing.json": {
                "name": "thing",
                "attributes": {
                    "scalar": {"name": "scalar", "type": "string_t"},
                    "other": {"name": "other", "type": "person"},
                    "self_ref": dict(
                        {"name": "self_ref", "type": "thing"},
                        **({RECURSIVE_KEY: annotation} if annotation else {}),
                    ),
                },
            },
            "/objects/person.json": {
                "name": "person",
                "attributes": {
                    "manager": dict(
                        {"name": "manager", "type": "user"},
                        **(
                            {RECURSIVE_KEY: manager_annotation}
                            if manager_annotation
                            else {}
                        ),
                    ),
                },
            },
            "/objects/user.json": {
                "name": "user",
                "attributes": {
                    "person": {
                        "name": "person",
                        "type": "person",
                        RECURSIVE_KEY: {"message": "m", "path": ["person.manager"]},
                    },
                },
            },
        }
    )


def test_validate_recursive_attrs_requires_annotation():
    r = _recursion_reader()

    with pytest.raises(MissingRecursiveAnnotationError) as exc:
        validate_recursive_attrs(r)
    assert exc.value.attr == "self_ref"
    assert exc.value.cycle == [("thing", "self_ref")]


def test_validate_recursive_attrs_accepts_annotation():
    r = _recursion_reader(
        annotation={"message": "Top-level only.", "limit": 1},
        manager_annotation={"message": "Reenters via user.", "path": ["user.person"]},
    )

    # raise no errors
    validate_recursive_attrs(r)


def test_validate_recursive_attrs_rejects_unnecessary_annotation():
    r = _recursion_reader(
        manager_annotation={"message": "m", "path": ["user.person"]},
    )
    r["/objects/thing.json"]["attributes"]["scalar"][RECURSIVE_KEY] = {"message": "m"}
    r["/objects/thing.json"]["attributes"]["self_ref"][RECURSIVE_KEY] = {"message": "m"}

    with pytest.raises(UnnecessaryRecursiveAnnotationError) as exc:
        validate_recursive_attrs(r)
    assert exc.value.attr == "scalar"


def test_validate_recursive_attrs_rejects_reference_into_a_cycle():
    """`thing.other` reaches a cycle but is not on one, so it is not recursive."""
    r = _recursion_reader(
        annotation={"message": "m"},
        manager_annotation={"message": "m", "path": ["user.person"]},
    )
    r["/objects/thing.json"]["attributes"]["other"][RECURSIVE_KEY] = {"message": "m"}

    with pytest.raises(UnnecessaryRecursiveAnnotationError) as exc:
        validate_recursive_attrs(r)
    assert exc.value.attr == "other"


def test_validate_recursive_attrs_checks_indirect_path():
    r = _recursion_reader(
        annotation={"message": "m"},
        manager_annotation={"message": "m", "path": ["user.somewhere_else"]},
    )

    with pytest.raises(InvalidRecursionPathError) as exc:
        validate_recursive_attrs(r)
    assert exc.value.attr == "manager"


def test_validate_recursive_attrs_rejects_path_on_direct_recursion():
    r = _recursion_reader(
        annotation={"message": "m", "path": ["thing.self_ref"]},
        manager_annotation={"message": "m", "path": ["user.person"]},
    )

    with pytest.raises(InvalidRecursionPathError) as exc:
        validate_recursive_attrs(r)
    assert exc.value.attr == "self_ref"


@pytest.mark.parametrize("path", [None, "person.manager", ["person.manager", 7], [{}]])
def test_validate_recursive_attrs_reports_malformed_path(path):
    """A `path` that is not a walk is reported, never raised.

    An exception here would escape the runner's `test()` helper, which exits 0
    and skips every later check, so a bad annotation would silently disable
    metaschema validation.
    """
    r = _recursion_reader(
        annotation={"message": "m"},
        manager_annotation={"message": "m", "path": path},
    )

    with pytest.raises(InvalidRecursionPathError) as exc:
        validate_recursive_attrs(r)
    assert exc.value.attr == "manager"
    # The message has to render whatever was in the file.
    assert "manager" in str(exc.value)


def _two_cycle_reader(x_path):
    """`a.x` sits on both a two-hop and a three-hop cycle back to `a`."""
    return DictReader(
        {
            "/objects/a.json": {
                "name": "a",
                "attributes": {
                    "x": {
                        "name": "x",
                        "type": "b",
                        RECURSIVE_KEY: {"message": "m", "path": x_path},
                    }
                },
            },
            "/objects/b.json": {
                "name": "b",
                "attributes": {
                    "direct": {
                        "name": "direct",
                        "type": "a",
                        RECURSIVE_KEY: {"message": "m", "path": ["a.x"]},
                    },
                    "detour": {
                        "name": "detour",
                        "type": "c",
                        RECURSIVE_KEY: {"message": "m", "path": ["c.back", "a.x"]},
                    },
                },
            },
            "/objects/c.json": {
                "name": "c",
                "attributes": {
                    "back": {
                        "name": "back",
                        "type": "a",
                        RECURSIVE_KEY: {"message": "m", "path": ["a.x", "b.detour"]},
                    }
                },
            },
        }
    )


def test_validate_recursive_attrs_accepts_a_longer_closing_walk():
    """`path` may name any simple cycle, not only the shortest one."""
    # raise no errors: the three-hop walk closes just as the two-hop one does
    validate_recursive_attrs(_two_cycle_reader(["b.detour", "c.back"]))
    validate_recursive_attrs(_two_cycle_reader(["b.direct"]))


def test_validate_recursive_attrs_rejects_a_walk_that_does_not_close():
    with pytest.raises(InvalidRecursionPathError) as exc:
        validate_recursive_attrs(_two_cycle_reader(["b.detour"]))
    assert exc.value.attr == "x"


def test_validate_recursive_attrs_after_process_includes():
    """`network_proxy` only recurses once it inherits from `network_endpoint`.

    This is why the check is ordered after the merge, so it is exercised
    through `process_includes` rather than against pre-resolved attributes.
    """
    data = {
        "/dictionary.json": {
            "attributes": {
                "proxy_endpoint": {
                    "caption": "",
                    "description": "",
                    "type": "network_proxy",
                },
                "port": {"caption": "", "description": "", "type": "port_t"},
            }
        },
        "/objects/network_endpoint.json": {
            "name": "network_endpoint",
            "caption": "",
            "attributes": {"port": {"requirement": "optional"}},
        },
        "/objects/network_proxy.json": {
            "name": "network_proxy",
            "caption": "",
            "extends": "network_endpoint",
            "attributes": {},
        },
    }

    # Before the merge, network_proxy has no attributes of its own and the
    # recursion is invisible.
    untouched = DictReader(deepcopy(data))
    validate_recursive_attrs(untouched)

    # network_endpoint gains proxy_endpoint, so network_proxy inherits it and
    # the edge closes on itself.
    data["/objects/network_endpoint.json"]["attributes"]["proxy_endpoint"] = {
        "requirement": "optional"
    }

    merged = DictReader(deepcopy(data))
    process_includes(merged)
    with pytest.raises(MissingRecursiveAnnotationError) as exc:
        validate_recursive_attrs(merged)
    assert exc.value.attr == "proxy_endpoint"
    assert exc.value.cycle == [("network_proxy", "proxy_endpoint")]

    # Annotating it on network_proxy satisfies the check, and network_endpoint
    # stays clean because nothing leads back to it.
    data["/objects/network_proxy.json"]["attributes"]["proxy_endpoint"] = {
        RECURSIVE_KEY: {"message": "Chains have no fixed depth."}
    }
    annotated = DictReader(deepcopy(data))
    process_includes(annotated)
    validate_recursive_attrs(annotated)


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
                    "gamma_t": {
                        "caption": "Gamma_T",
                        "type": "string_t",
                        "type_name": "String",
                    },
                    "delta_t": {
                        "caption": "Delta_T",
                        "type": "integer_t",
                        "type_name": "Integer",
                        "observable": 2,
                    },
                },
            },
        },
        "/objects/bird.json": {
            "name": "bird",
            "caption": "Bird",
            "attributes": {
                "name": {"requirement": "required"},
                "alpha": {"requirement": "required"},
            },
        },
        "/objects/cat.json": {
            "name": "cat",
            "caption": "Cat",
            "observable": 10,
            "attributes": {
                "name": {"requirement": "required"},
                "alpha": {"requirement": "required"},
            },
        },
        "/objects/dog.json": {
            "name": "dog",
            "caption": "Dog",
            "attributes": {
                "name": {"requirement": "required"},
                "alpha": {"requirement": "required", "observable": 11},
            },
        },
        "/objects/dog_house.json": {
            "name": "dog_house",
            "caption": "Dog House",
            "attributes": {"tenant": {"type": "dog", "requirement": "required"}},
            "observables": {"dog.name": 12},
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
        },
        "/events/red.json": {
            "uid": 3,
            "name": "red",
            "caption": "Red",
            "attributes": {"beta": {"requirement": "required", "observable": 100}},
        },
        "/events/yellow.json": {
            "uid": 4,
            "name": "yellow",
            "caption": "Yellow",
            "attributes": {"bird": {"requirement": "required"}},
            "observables": {"bird.name": 101},
        },
    }

    observables = validate_and_get_observables(DictReader(good_data))
    assert observables is not None
    assert len(observables) == 6
    print("\ntest_validate_observables - collected observables:")
    print(observables_to_string(observables))

    with pytest.raises(IllegalObservableTypeIDError):
        bad_data = dict(good_data)
        bad_data["/objects/_hidden.json"] = {
            "name": "_hidden",
            "caption": "Hidden",
            "observable": 1,
        }
        validate_observables(DictReader(bad_data))

    with pytest.raises(IllegalObservableTypeIDError):
        bad_data = dict(good_data)
        bad_data["/objects/_hidden.json"] = {
            "name": "_hidden",
            "caption": "Hidden",
            "attributes": {"beta": {"requirement": "required", "observable": 1}},
        }
        validate_observables(DictReader(bad_data))

    with pytest.raises(IllegalObservableTypeIDError):
        bad_data = dict(good_data)
        bad_data["/events/_hidden.json"] = {
            "name": "hidden",
            "caption": "Hidden",
            "attributes": {"beta": {"requirement": "required", "observable": 1}},
        }
        validate_observables(DictReader(bad_data))

    with pytest.raises(ObservableTypeIDCollisionError):
        bad_data = dict(good_data)
        dictionary_attributes = bad_data["dictionary.json"]["attributes"]
        dictionary_attributes["epsilon"] = {
            "caption": "Epsilon",
            "type": "string_t",
            "observable": 1,
        }
        validate_observables(DictReader(bad_data))

    with pytest.raises(ObservableTypeIDCollisionError):
        bad_data = dict(good_data)
        dictionary_types_attributes = bad_data["dictionary.json"]["types"]["attributes"]
        dictionary_types_attributes["epsilon_t"] = (
            {
                "caption": "Epsilon_T",
                "type": "string_t",
                "type_name": "String",
                "observable": 2,
            },
        )
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

    bad_data = {
        "categories.json": {
            "attributes": {
                "alpha": {"caption": "Alpha", "uid": 1},
                "beta": {"caption": "Beta", "uid": 2},
            }
        },
        "events/foo.json": {"caption": "Foo", "category": "alpha"},
        "events/bar.json": {"caption": "Bar", "category": "gamma"},
        "events/baz.json": {"caption": "Baz", "category": "other"},
        "events/guux.json": {"caption": "Quux"},
    }
    with pytest.raises(UnknownCategoryError):
        validate_event_categories(DictReader(bad_data))


def test_validate_metaschemas():
    # set up a json schema that expects an object with a name property only
    object_json_schema = {
        "$id": "https://fake.schema.ocsf.io/object.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Object",
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
        "additionalProperties": False,
    }

    def _get_registry(reader, base_uri) -> referencing.Registry:
        registry: referencing.Registry = referencing.Registry()
        for schema in METASCHEMA_MATCHERS.keys():
            resource = referencing.Resource.from_contents(object_json_schema)  # type: ignore
            registry = registry.with_resource(base_uri + schema, resource=resource)
        return registry

    options = ReaderOptions(base_path=Path(""))

    # test that a bad schema fails validation
    r = DictReader(options)
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
    r = DictReader(options)
    r.set_data(
        {
            "/objects/thing.json": {
                "name": "thing",
            },
        }
    )

    validate_metaschemas(r, get_registry=_get_registry)

    # test that a good schema passes validation
    r = DictReader(options)
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


def test_constraint_members_must_be_recommended():
    r = DictReader()
    r.set_data(
        {
            "/objects/user.json": {
                "name": "user",
                "attributes": {
                    "account": {"requirement": "recommended"},
                    "name": {"requirement": "recommended"},
                },
                "constraints": {"at_least_one": ["account", "name"]},
            }
        }
    )
    validate_constraint_requirements(r)


def test_constraint_member_optional_is_reported():
    r = DictReader()
    r.set_data(
        {
            "/objects/user.json": {
                "name": "user",
                "attributes": {
                    "account": {"requirement": "optional"},
                    "name": {"requirement": "recommended"},
                },
                "constraints": {"at_least_one": ["account", "name"]},
            }
        }
    )
    with pytest.raises(ConstraintMemberRequirementError) as exc:
        validate_constraint_requirements(r)
    assert exc.value.member == "account"
    assert exc.value.kind == "at_least_one"


def test_constraint_member_required_is_reported():
    r = DictReader()
    r.set_data(
        {
            "/objects/aircraft.json": {
                "name": "aircraft",
                "attributes": {"uid": {"requirement": "required"}},
                "constraints": {"just_one": ["uid"]},
            }
        }
    )
    with pytest.raises(ConstraintMemberRequiredError) as exc:
        validate_constraint_requirements(r)
    assert exc.value.member == "uid"
    assert exc.value.kind == "just_one"


def test_constraint_member_missing_is_reported():
    r = DictReader()
    r.set_data(
        {
            "/events/system/event_log_activity.json": {
                "name": "event_log_activity",
                "attributes": {"log_name": {"requirement": "recommended"}},
                "constraints": {"at_least_one": ["log_file", "log_name"]},
            }
        }
    )
    with pytest.raises(ConstraintMemberMissingError) as exc:
        validate_constraint_requirements(r)
    assert exc.value.member == "log_file"


def test_dotted_constraint_member_uses_nested_requirement():
    r = DictReader()
    r.set_data(
        {
            "/objects/os.json": {
                "name": "os",
                "attributes": {
                    "version": {"requirement": "optional", "type": "string_t"}
                },
            },
            "/objects/device.json": {
                "name": "device",
                "attributes": {"os": {"requirement": "required", "type": "os"}},
            },
            "/events/discovery/patch_state.json": {
                "name": "patch_state",
                "attributes": {"device": {"requirement": "required", "type": "device"}},
                "constraints": {"at_least_one": ["device.os.version"]},
            },
        }
    )
    with pytest.raises(ConstraintMemberRequirementError) as exc:
        validate_constraint_requirements(r)
    assert exc.value.member == "device.os.version"
    assert exc.value.file == "/events/discovery/patch_state.json"


def test_inherited_constraint_member_requirement():
    r = DictReader()
    r.set_data(
        {
            "/dictionary.json": {"attributes": {}},
            "/objects/entity.json": {
                "name": "entity",
                "attributes": {
                    "name": {"requirement": "recommended"},
                    "uid": {"requirement": "recommended"},
                },
                "constraints": {"at_least_one": ["name", "uid"]},
            },
            "/objects/user.json": {
                "name": "user",
                "extends": "entity",
                "attributes": {"name": {"requirement": "optional"}},
            },
        }
    )
    process_includes(r, collector=Collector(throw=False))
    with pytest.raises(ConstraintMemberRequirementError) as exc:
        validate_constraint_requirements(r)
    assert exc.value.member == "name"
    assert exc.value.file == "/objects/user.json"


def test_empty_constraints_clear_the_parent_constraint():
    r = DictReader()
    r.set_data(
        {
            "/dictionary.json": {"attributes": {}},
            "/objects/entity.json": {
                "name": "entity",
                "attributes": {
                    "name": {"requirement": "recommended"},
                    "uid": {"requirement": "recommended"},
                },
                "constraints": {"at_least_one": ["name", "uid"]},
            },
            "/objects/file.json": {
                "name": "file",
                "extends": "entity",
                "attributes": {},
                "constraints": {},
            },
        }
    )
    process_includes(r, collector=Collector(throw=False))
    assert r["/objects/file.json"]["constraints"] == {}
    validate_constraint_requirements(r)


def test_extension_patch_resolves_extended_object_attributes():
    r = DictReader()
    r.set_data(
        {
            "/objects/evidences.json": {
                "name": "evidences",
                "attributes": {"actor": {"requirement": "recommended"}},
                "constraints": {"at_least_one": ["actor"]},
            },
            "/extensions/windows/objects/evidences.json": {
                "extends": "evidences",
                "attributes": {"win_service": {"requirement": "recommended"}},
                "constraints": {"at_least_one": ["actor", "win_service"]},
            },
        }
    )
    validate_constraint_requirements(r)


def test_constraint_severities():
    from ocsf_validator.runner import Severity, ValidatorOptions

    options = ValidatorOptions()
    assert (
        options.severity(
            ConstraintMemberRequirementError("at_least_one", "a", "f", "optional")
        )
        == Severity.ERROR
    )
    assert (
        options.severity(ConstraintMemberMissingError("at_least_one", "log_file", "f"))
        == Severity.ERROR
    )
    assert (
        options.severity(ConstraintMemberRequiredError("at_least_one", "name", "f"))
        == Severity.WARN
    )
