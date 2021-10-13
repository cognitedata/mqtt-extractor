import importlib
import logging
import sys
import time
from dataclasses import dataclass, field
from threading import Event
from typing import List

from cognite.client import CogniteClient
from cognite.client.data_classes import ExtractionPipelineRun
from cognite.extractorutils.configtools import (
    BaseConfig,
    load_yaml,
)
from cognite.extractorutils.uploader import TimeSeriesUploadQueue
from paho.mqtt.client import Client as MqttClient

from . import metrics

logger = logging.getLogger(__name__)


@dataclass
class MqttConfig:
    hostname: str
    port: int
    username: str = None
    password: str = None
    client_id: str = "mqtt-extractor"
    clean_session: bool = False

@dataclass
class Handler:
    module: str = "mqtt_extractor.cdf"
    function: str = "parse"
    package: str = None

    def handler(self):
        module = importlib.import_module(self.module, self.package)
        return getattr(module, self.function)


@dataclass
class Subscription:
    topic: str
    handler: Handler = field(default_factory=Handler)
    qos: int = 0

@dataclass
class Config(BaseConfig):
    mqtt: MqttConfig
    subscriptions: List[Subscription]
    upload_interval: int = 1
    create_missing: bool = True
    status_pipeline: str = None
    status_interval: int = 60


def config_logging(config_file):
    from yaml import safe_load

    logger_format = "%(asctime)s.%(msecs)03d %(levelname)-8s %(name)-22s %(message)s"
    logging.basicConfig(format=logger_format, datefmt="%Y-%m-%d %H:%M:%S")
    if config_file:
        with open(config_file) as f:
            logging.config.dictConfig(safe_load(f))


_handlers = {}


def on_connect(client, userdata, flags, rc):
    logger.info("Connection to MQTT server open")
    # logger.info("Flags %s", flags)
    if flags.get("session present") != 1:
        # Should have session state for QoS=1
        logger.warning("MQTT connection without session state")
    for subscription in config.subscriptions:
        logger.info("MQTT subscribe: %s", subscription)
        handler = subscription.handler.handler()
        _handlers[subscription.topic] = handler
        # logger.info("Handler: %r %r", subscription.handler, handler)
        client.subscribe(subscription.topic, qos=subscription.qos)


def on_disconnect(client, userdata, flags):
    logger.warning("Connection to MQTT server closed")


def mqtt_client(config: MqttConfig):
    logger.info("MQTT client to %s:%d", config.hostname, config.port)
    client = MqttClient(client_id=config.client_id, clean_session=config.clean_session)
    client.username_pw_set(
        username=config.username,
        password=config.password,
    )
    client.enable_logger()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect_async(config.hostname, config.port)
    client.loop_start()
    return client


def now() -> int:
    return int(1000 * time.time())


def main():

    with open(sys.argv[1]) as config_file:
        global config
        config = load_yaml(config_file, Config)

    config.logger.setup_logging()

    logger.info("MQTT to CDF extractor")

    cdf_client = config.cognite.get_cognite_client("mqtt-extractor")

    client = mqtt_client(config.mqtt)

    message_time_stamp = 0
    cdf_time_stamp = 0
    status_time_stamp = 0

    def post_upload_handler(ts_dps):
        dps = sum(len(ts["datapoints"]) for ts in ts_dps)
        metrics.cdf_data_points.inc(dps)
        logger.info("Uploaded %d data points", dps)
        logger.debug("Uploaded %r", ts_dps)
        if not ts_dps:
            # calls the handler with empty ts_dps when API call fails.
            # max([]) fails below but could use default=... argument.
            metrics.cdf_requests_failed.inc()
            return
        try:
            if 0:
                time_stamp = max(max(ts["datapoints"]["timestamp"]) for ts in ts_dps)
                nonlocal cdf_time_stamp
                if time_stamp > cdf_time_stamp:
                    cdf_time_stamp = time_stamp
                    metrics.cdf_time_stamp.set(cdf_time_stamp)

            if config.status_pipeline:
                # "success" (should be "seen") heart beat after uploading data points to CDF
                nonlocal status_time_stamp
                t = now()
                if t >= status_time_stamp:
                    cdf_client.extraction_pipeline_runs.create(
                        ExtractionPipelineRun(status="success", external_id=config.status_pipeline)
                    )
                    status_time_stamp = t + 1000 * config.status_interval
        except Exception:
            # Risk of too many stack traces?
            logger.exception("post upload handler")

    stop = Event()

    with TimeSeriesUploadQueue(
        cdf_client,
        post_upload_function=post_upload_handler,
        max_upload_interval=config.upload_interval,
        trigger_log_level="INFO",
        thread_name="CDF-Uploader",
        create_missing=config.create_missing,
    ) as upload_queue:
 
        def on_message(client, userdata, message):
            try:
                nonlocal message_time_stamp
                logger.debug(
                    "Message %s %d %s",
                    message.topic,
                    len(message.payload),
                    repr(message.payload[:16]),
                )

                handle = _handlers.get(message.topic)
                if not handle:
                    logger.debug("Unhandled topic: %s", message.topic)
                    return
                    
                for ts_id, time_stamp, value in handle(message.payload, message.topic):

                    logger.debug("Data point %s %d %r", ts_id, time_stamp, value)
                    external_id = config.cognite.external_id_prefix + ts_id

                    # Add to TS upload queue
                    if time_stamp is not None and value is not None:
                        upload_queue.add_to_upload_queue(
                            external_id=external_id, datapoints=[(time_stamp, value)]
                        )

                    if time_stamp > message_time_stamp:
                        message_time_stamp = time_stamp
                
                # Upload any remaining TS in queue
                upload_queue.upload()

                metrics.messages.inc()
                metrics.message_time_stamp.set(message_time_stamp)
            except Exception:
                logger.exception("on_message")

        client.on_message = on_message
        stop.wait()

    if config.metrics:
        config.metrics.stop_pushers()

    logger.info("Extractor stopped")


if __name__ == "__main__":
    main()
