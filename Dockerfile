#  a Dockerfile to containerize the build of ocsf-validator
#
#  To build a container:
#
#     docker build -t ocsf-validator:latest .
#
#  To use it to validate a schema
#
#     docker run --rm -v $PWD:/schema ocsf-validator:latest /schema
#

FROM python:3.11.9-alpine3.19

RUN apk add --no-cache poetry nodejs npm

WORKDIR /src

# install stuff that doesn't change much
ADD poetry.lock pyproject.toml .
RUN poetry install --no-root

# pull in the rest of the code
ADD . .
RUN poetry install --only-root
RUN poetry run black .
RUN poetry run isort .
RUN poetry run pyright ocsf_validator
RUN poetry run pytest

ENTRYPOINT ["poetry", "run", "python", "-m", "ocsf_validator"]
