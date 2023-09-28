# OCSF Schema Validator

## Structure

In short:

 - The `Reader`s in `reader.py` represent collections of unprocessed, unvalidated schema definitions. Of these, `FileReader` reads files from a copy of the `ocsf-schema` repository, so it's probably the one you want.
 - `errors.py` contains exceptions raised by validation steps that inherit from `ValidationError`, as well as a special error `Collector`. Throughout this package, non-fatal exceptions are sent to a `Collector` instead of being `raise`d. The `Collector` will raise exceptions by default, but can also collect them to be dealt with later. The `ValidationRunner` exploits this for pretty output of failed validations.
 - The processor functions in `processors.py` apply includes, inheritance, and profiles to otherwise partial schema definitions. They also merge attribute details from `dictionary.json`. Be warned that these functions are side-effecting: they operate directly on the schema definitions in a `Reader`. This doesn't sit well with me, but passing lots of copies of the whole schema around didn't feel right, either, and this package is meant to be single-threaded.
 - The validator functions in `validators.py` test schema definitions for various problematic conditions. If you're extending this module, chances are you want to add validators.
 - The `ValidationRunner` in `runner.py` is a convenient command line entry point for validating a copy of the OCSF schema. It ties together the building blocks above.


## Running the validator

```
poetry run python -m ocsf_validator.runner <schema_path>
```

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

### General

 - [ ] Include all paths and types in validation
 - [ ] Are things named consistently across (and within) modules?
 - [ ] Inline documentation could be better.
 - [ ] This README could be better.
 - [ ] Shell script to run tests and formatters.
 - [ ] Clean up * imports, especially in `__init__.py`.
 - [ ] Consider any imports in `__init__.py` that could be package-protected.

### Processors

 - [X] Refactor optional match mode parameters to be a Match object with a Pattern type of str | Match.
 - [X] Canned patterns for event, object, etc.
 - [X] Type detection of records based on key.
 - [X] Cyclical dependencies...
 - [ ] Exclude keys that match the included record type (e.g. OcsfProfile) but not the destination record type for flavors of include.
 - [ ] Refactor find_include, etc., from Reader to MergeParsers
 - [ ] Refactor reader and processor unit tests

### Runner

 - [ ] Write a shell script to run the ValidationRunner.
 - [ ] Refactor runner __main__ code to __main__.py
 - [ ] Show test summary at end of validation results instead of beginning

### Pipeline

 - [ ] Action for this repository to run formatters and tests on PRs.
 - [ ] Action for this repository to publish to PyPi
 - [ ] Action for the OCSF Schema repository to run the validation runner on PRs.

### Validators

 - [X] Required keys (including nested in attrs)
 - [X] No unknown keys
    - [ ] Fix "description:" key
 - [X] Include targets exist
 - [X] Profile targets exist
 - [X] Inheritance targets (`extends`) exist
 - [ ] Categories match directories in events
 - [X] Warn of unused dictionary items
 - [ ] Warn of unused enums
 - [ ] Warn of unused profiles
 - [ ] Warn of unused includes
 - [ ] Validate types for attributes
 - [ ] Type matching
 - [ ] Name collisions between extensions
 - [ ] Name collisions between objects and events
 - [ ] Warn of redundant `profiles` and `$include` targets (it is convention to have a `profiles` directive at the top level and an `$include` to the same profile in the `attributes` section, but the `$include` would fail and this seems redundant anyway).
