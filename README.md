# OCSF Schema Validator

A utility to validate contributions to the [OCSF
schema](https://github.com/ocsf/ocsf-schema), intended to prevent human error
when contributing to the schema in order to keep the schema machine-readable.

OCSF provides several include mechanisms to facilitate reuse, but this means
individual schema files may be incomplete. This complicates using off-the-shelf
schema definition tools for validation.

[Query](https://www.query.ai) is a federated search solution that normalizes
disparate security data to OCSF. This validator is adapted from active code and
documentation generation tools written by the Query team.


## Supported Validations

The validator can currently perform the following validations:

 - [X] All required keys are present
 - [X] There are no unrecognized keys
 - [X] Dependency targets are resolvable and exist
 - [X] All attributes in `dictionary.json` are used
 - [X] There are no redundant `profiles` and `$include` targets
 - [X] There are no name collisions within record types

## Planned Validations

In the future, this validation should also ensure the following:

 - [ ] The contents of `categories.json` match the directory structure of `/events`
 - [ ] There are no unused enums
 - [ ] There are no unused profiles
 - [ ] There are no unused imports
 - [ ] There are no name collisions between extensions
 - [ ] There are no name collisions between objects and events


## Running the validator

1. Install the validator using `pip` or `poetry`. (well, once we're publishing it...)
2. Clone a copy of the OCSF schema, if you don't already have one.
3. Invoke the validator with the location of your copy of the OCSF schema.

```
poetry run python -m ocsf_validator <schema_path>
```

## Technical Overview

The OCSF metaschema is represented as record types by filepath, achieved as follows:

 1. Record types are represented using Python's type system by defining them as Python `TypedDict`s in `types.py`. This allows the validator to take advantage of Python's reflection capabilities.
 2. Files and record types are associated by pattern matching the file paths. These patterns are named in `matchers.py` to allow mistakes to be caught by a type checker.
 3. Types are mapped to filepath patterns in `type_mapping.py`.

The contents of the OCSF schema to be validated are primarily represented as a `Reader` defined in `reader.py`. `Reader`s load the schema definitions to be validated from a source (usually from a filesystem) and contain them without judgement. The `process_includes` function and other contents of `processor.py` mutate the contents of a `Reader` by applying OCSF's various include mechanisms.

Validators are defined in `validators.py` and test the schema contents for various problematic conditions. Validators should pass `Exception`s to a special error `Collector` defined in `errors.py`. This module also defines a number of custom exception types that represent problematic schema states. The `Collector` raises errors by default, but can also hold them until they're aggregated by a larger validation process (e.g., the `ValidationRunner`).

The `ValidationRunner` combines all of the building blocks above to read a proposed schema from a filesystem, validate the schema, and provide useful output and a non-zero exit code if any errors were encountered.


## Notes on dependency resolution

OCSF provides several mechanisms for reusing schema definitions. They are implemented in `processor.py`, but it's a relatively large module. Below is a summary of dependency behavior in the validator.


### $include

The `$include` directive allows a record type author to include the contents of any other file. These directives are supported in many locations throughout the schema.

When an `$include` directive is used, the contents of the included file are merged inline. Properties in the included file will lose out over properties in the source file. If an `$include` directive is used in a nested dictionary, the processor will merge the contents of the same key in the included file. For instance, using an `$include: "B.json"` in the `attributes` key of `A.json` will merge the contents of the `attributes` key from `A.json` with the contents of the `attributes` key in `B.json`.

Include targets are assumed to be relative to the root of the schema or the root of the current extension.


### extends

`extends` directives work something like inheritance in OOP. The base record type targeted in an `extends` directive will be merged with the child record type. Any properties defined in the child record win. The first matching base record type will be the only one used.

For a requested base `b` from a child record at `events/activity/thing.json`, the search order will be:

- events/activity/b.json
- events/b.json

For a requested base `b` in a child record at `extn/stuff/events/activity/thing.json`, the search order will be:

- extn/stuff/events/activity/b.json
- events/activity/b.json
- extn/stuff/events/b.json
- events/b.json
- extn/stuff/b.json

There are events in the schema today that inherit from events in sibling categories. This seems potentially ambiguous, so a warning is generated. If the search orders above don't find a match, then all sibling directories will also be searched.


### profiles

A `profiles` directive references mix-in traits that can apply to the record for certain applications. Profiles are applied to records by `process_includes` so that their contents can be validated.


For a requested profile `p`, the search order will be:

- extn/profiles/p
- extn/profiles/p.json
- profiles/p
- profiles/p.json
- extn/p
- extn/p.json
- p
- p.json


### dictionary.json

The schema reuses attribute details from a shared attribute dictionary. Defining your record type with `attributes: { "one": {...}}` will cause the attribute details defined in `dictionary.json` to be merged with the attribute definition in the record type. Properties defined in the record type take precedence.

Attributes are currently compared by their key in the `attributes` dictionaries and not by their `name` property.


## Contributing

After checking out, you'll want to install dependencies:
```
poetry install
```

Before committing, run the formatters and tests:
```
poetry run isort
poetry run black
poetry run pyright
poetry run pytest
```

If you're adding a validator, do the following:
 - Write your `validate_` function in `validate.py` to apply a function to the relevant keys in a reader that will run your desired validation. See `validators.py` for examples.
 - Add any custom errors in `errors.py`.
 - Create an option to change its severity level in `ValidatorOptions` and map it in the constructor of `ValidationRunner` in `runner.py`.
 - Invoke the new validator in `ValidationRunner.validate`.


## TODO

There is still plenty to be done!

### General

 - [ ] Add CLI arguments for everything in ValidatorOptions
 - [ ] Add more validators.
 - [ ] Are things named consistently across (and within) modules?
 - [ ] Inline documentation could be better.
 - [ ] This README could be better.
 - [ ] Shell script to run tests and formatters.
 - [ ] Clean up * imports, especially in `__init__.py`.
 - [ ] Consider any imports in `__init__.py` that could be package-protected.

### Pipeline

 - [ ] Action for this repository to run formatters and tests on PRs.
 - [ ] Add a coverage report.
 - [ ] Action for this repository to publish to PyPi.
 - [ ] Action for the OCSF Schema repository to run the validation runner on PRs.

### Testing

 - [ ] Unit tests for TypeMapping
 - [ ] Test coverage could be a lot better in general
