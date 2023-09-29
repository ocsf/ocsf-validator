# OCSF Schema Validator

A utility to validate contributes to the OCSF Schema.

The [OCSF Schema](https://github.com/ocsf/ocsf-schema) is defined

## Current Validations

The validator can currently perform the following validations:

 - [X] All required keys are present
 - [X] There are no unknown keys
 - [X] Dependency targets are resolvable and exist
 - [X] All attributes in `dictionary.json` are used
 - [X] There are no redundant `profiles` and `$include` targets

## Future Validations

In the future, this validation should also ensure the following:

 - [ ] The contents of `categories.json` match the directory structure of `/events`
 - [ ] There are no unused enums
 - [ ] There are no unused profiles
 - [ ] There are no unused imports
 - [ ] There are no name collisions between extensions
 - [ ] There are no name collisions between objects and events


## Running the validator

```
poetry install
poetry run python -m ocsf_validator <schema_path>
```

## Package Structure

In short:

 - The `Reader`s in `reader.py` represent collections of unprocessed, unvalidated schema definitions. Of these, `FileReader` reads files from a copy of the `ocsf-schema` repository, so it's probably the one you want.
 - `errors.py` contains exceptions raised by validation steps that inherit from `ValidationError`, as well as a special error `Collector`. Throughout this package, non-fatal exceptions are sent to a `Collector` instead of being `raise`d. The `Collector` will raise exceptions by default, but can also collect them to be dealt with later. The `ValidationRunner` exploits this for pretty output of failed validations.
 - The contents of `processor.py` apply includes, inheritance, and profiles to otherwise partial schema definitions. They also merge attribute details from `dictionary.json`. Be warned that these processors are side-effecting: they operate directly on the schema definitions in a `Reader`. You'll probably just want to invoke `process_includes` and run away.
 - The validator functions in `validators.py` test schema definitions for various problematic conditions. If you're extending this module, chances are you want to add validators.
 - The `ValidationRunner` in `runner.py` is a convenient command line entry point for validating a copy of the OCSF schema. It ties together the building blocks above.


## Enhancing the validator

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
