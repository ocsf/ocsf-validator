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

## Getting Started

### Prerequisites

 - python >3.11
 - pip
 - A copy of the [OCSF schema](https://github.com/ocsf/ocsf-schema)

### Installation

You can install the validator with `pip`:

```
$ pip install ocsf-validator
```

## Usage

You can run the validator against your working copy of the schema to identify problems before submitting a PR. Invoke the validator using `python` and provide it with the path to the root of your working copy.

Examples:
```
$ python -m ocsf_validator .
$ python -m ocsf_validator ../ocsf-schema
```


## Tests

The validator performs the following tests on a copy of the schema:

 - The schema is readable and all JSON is valid. [FATAL]
 - The directory structure meets expectations. [WARNING]
 - The targets in `$include`, `profiles`, and `extends` directives can be found. [ERROR]
 - All required attributes in schema definition files are present. [WARNING]
 - There are no unrecognized attributes in schema definition files. [WARNING]
 - All attributes in the attribute dictionary are used. [WARNING]
 - There are no name collisions within a record type. [WARNING]
 - All attributes are defined in the attribute dictionary. [WARNING]

If any ERROR or FATAL tests fail, the validator exits with a non-zero exit code.


## Technical Overview

The OCSF metaschema is represented as record types by filepath, achieved as follows:

 1. Record types are represented using Python's type system by defining them as Python `TypedDict`s in `types.py`. This allows the validator to take advantage of Python's reflection capabilities.
 2. Files and record types are associated by pattern matching the file paths. These patterns are named in `matchers.py` to allow mistakes to be caught by a type checker.
 3. Types are mapped to filepath patterns in `type_mapping.py`.

The contents of the OCSF schema to be validated are primarily represented as a `Reader` defined in `reader.py`. `Reader`s load the schema definitions to be validated from a source (usually from a filesystem) and contain them without judgement. The `process_includes` function and other contents of `processor.py` mutate the contents of a `Reader` by applying OCSF's various include mechanisms.

Validators are defined in `validators.py` and test the schema contents for various problematic conditions. Validators should pass `Exception`s to a special error `Collector` defined in `errors.py`. This module also defines a number of custom exception types that represent problematic schema states. The `Collector` raises errors by default, but can also hold them until they're aggregated by a larger validation process (e.g., the `ValidationRunner`).

The `ValidationRunner` combines all of the building blocks above to read a proposed schema from a filesystem, validate the schema, and provide useful output and a non-zero exit code if any errors were encountered.


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
