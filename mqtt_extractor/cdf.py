from json import loads
import logging

logger = logging.getLogger(__name__)


def parse(payload: bytes, topic: str):
    logger.info("Payload type: %s", type(payload))
    msg = loads(payload)
    logger.debug("Message: %r %r", topic, msg)
    for item in msg["items"]:
        extid = item["externalId"]
        for dp in item["datapoints"]:
            timestamp = dp["timestamp"]
            value = dp["value"]
            yield extid, timestamp, value
