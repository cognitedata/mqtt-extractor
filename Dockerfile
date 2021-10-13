FROM python:3.8-slim-buster as requirements

RUN python -m pip install --upgrade pip
RUN python -m pip install --upgrade poetry
RUN poetry config virtualenvs.create false

WORKDIR /cognite

COPY pyproject.toml ./
COPY poetry.lock ./
RUN poetry export --without-hashes -f requirements.txt --output requirements.txt

FROM python:3.8-slim-buster
RUN python -m pip install --upgrade pip
WORKDIR /cognite
COPY --from=requirements /cognite/requirements.txt .
RUN python -m pip install --force-reinstall -r requirements.txt

ADD mqtt_extractor ./mqtt_extractor

ENTRYPOINT [ "python", "-m", "mqtt_extractor.main", "config/config.yaml" ]
