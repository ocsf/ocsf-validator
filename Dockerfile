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
ADD . .

RUN poetry install
RUN poetry run black .
RUN poetry run isort .
RUN poetry run pyright ocsf_validator
RUN poetry run pytest

ENTRYPOINT ["poetry", "run", "python", "-m", "ocsf_validator"]
