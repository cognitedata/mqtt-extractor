# mqtt-extractor

Pushing data points and time series to CDF from a MQTT service.

## Development

Install poetry:

    python -m pip install --upgrade pip && pip install poetry

Install dependencies:

    poetry install

Run unit tests (use `-s` to show print() debug output):

    poetry run pytest -s

Run a local MQTT service:

    docker run --name mqtt --rm -d -p 1883:1883 eclipse-mosquitto:1.6

Run the simulation publishing messages to the local MQTT service:

    poetry run sim

Configure and run the extractor:

    poetry run main config/config.yaml

## Docker

Build docker image locally:

    docker build . -t mqtt-extractor

Test the docker image locally:

    docker run --rm --name mqtt-extractor -v $PWD/config:/cognite/config mqtt-extractor

Run docker container from local build mounting the local config file:

    docker run -d --restart unless-stopped --name mqtt-extractor --log-driver json-file --log-opt max-size=10m -v $HOME/config:/cognite/config mqtt-extractor
