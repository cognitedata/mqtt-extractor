import json
import logging
import time

from paho.mqtt.client import Client as MqttClient

logger = logging.getLogger(__name__)


def on_connect(client, userdata, flags, rc):
    logger.info("Connection to MQTT server open")


def on_disconnect(client, userdata, flags):
    logger.warning("Connection to MQTT server closed")


def mqtt_client(hostname: str, port: int):
    client = MqttClient()
    client.enable_logger(logger)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect_async(hostname, port)
    client.loop_start()
    return client


def now() -> int:
    return int(1000 * time.time())


def main():
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Starting CDF payload publisher")
    client = mqtt_client("localhost", 1883)

    topic = "cdf"
    n = 10

    value = 1
    while True:
        t = now()
        items = []
        for i in range(n):
            items.append({
                "externalId": f"cdf_int{i}",
                "datapoints": [{"timestamp": t, "value": value}]
            })
            items.append({
                "externalId": f"cdf_str{i}",
                "datapoints": [{"timestamp": t, "value": str(value)}]
            })

        message = { "items": items }
        logger.debug("Publish %r", message)
        client.publish(topic, json.dumps(message))
        time.sleep(1)
        value += 1


if __name__ == "__main__":
    main()
