#!/bin/sh

if ! [ "${0}" -ef "${PWD}/build.sh" ]; then
  echo "build.sh must be run from project root" >&2
  exit 1
fi

if [ "${VIRTUAL_ENV}" = "" ]; then
  exec poetry run "$0"
fi

poetry install --no-root

black .
isort .
pyright ocsf_validator
pytest
