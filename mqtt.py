#!/usr/bin/env python3

import asyncio
import datetime
import logging
import os
import time

from zoneinfo import ZoneInfo
import aiomqtt

from meshdecoder.meshinfo_decoder import MeshInfoParser, MeshInfoHandler


class MQTT:
    def __init__(self, config, data):
        self.config = config
        self.data = data

        self.host = config['broker']['host']
        self.port = config['broker']['port']
        self.client_id = config['broker']['client_id']
        self.username = config['broker']['username']
        self.password = config['broker']['password']

        self.parser = MeshInfoParser(
            mesh_db=self.data, json_enabled=self.config['broker']['decoders']['json']['enabled'])
        self.handler = MeshInfoHandler(
            mesh_db=self.data, meshinfo_config=config, loop=asyncio.get_event_loop())

        # setup logging
        os.makedirs(f"{self.config['paths']['data']}", exist_ok=True)
        error_log_handler = logging.FileHandler(
            f"{self.config['paths']['data']}/error.log")
        error_log_handler.setLevel(logging.ERROR)
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s [%(levelname)s] %(message)s",
                            handlers=[
                                error_log_handler,
                                logging.StreamHandler()
                            ]
                            )

    # actions

    async def connect(self):
        await self.handler.start()

        logging.info(
            f"Connecting to MQTT broker at {self.config['broker']['host']}:{self.config['broker']['port']}")
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=self.config["broker"]["host"],
                    port=self.config["broker"]["port"],
                    identifier=self.config["broker"]["client_id"],
                    username=self.config["broker"]["username"],
                    password=self.config["broker"]["password"],
                ) as client:
                    logging.info("Connected to MQTT broker at %s:%d" % (
                        self.config["broker"]["host"],
                        self.config["broker"]["port"],
                    ))
                    if "topics" in self.config["broker"] and self.config["broker"]["topics"] is not None and isinstance(self.config["broker"]["topics"], list):
                        for topic in self.config["broker"]["topics"]:
                            await client.subscribe(topic)
                    elif "topic" in self.config["broker"] and self.config["broker"]["topic"] is not None and isinstance(self.config["broker"]["topic"], str):
                        await client.subscribe(self.config["broker"]["topic"])
                    else:
                        logging.error(
                            "No MQTT topics to subscribe to defined in config broker.topics or broker.topic")
                        exit(1)

                    self.data.mqtt_connect_time = datetime.datetime.now(
                        ZoneInfo(self.config['server']['timezone']))
                    async for msg in client.messages:
                        # paho adds a timestamp to messages which is not in
                        # aiomqtt. We will do that ourself here so it is compatible.
                        msg.timestamp = time.monotonic()  # type: ignore
                        await self.process_mqtt_msg(client, msg)
            except aiomqtt.MqttError as err:
                logging.info(
                    f"Disconnected from MQTT broker: {err}\nReconnecting...")
                await asyncio.sleep(5)

    async def process_mqtt_msg(self, client, msg):
        packet, meta = self.parser.parseMQTT(msg)
        await self.handler.handle_packet(packet=packet, meta=meta)

    async def publish(self, client, topic, msg):
        result = await client.publish(topic, msg)
        status = result[0]
        if status == 0:
            logging.info(f"Send `{msg}` to topic `{topic}`")
            return True
        else:
            logging.warning(f"Failed to send message to topic {topic}")
            return False

    async def subscribe(self, client, topic):
        client.subscribe(topic)
        logging.info(f"Subscribed to topic `{topic}`")

    async def unsubscribe(self, client, topic):
        client.unsubscribe(topic)

    # TODO: where should this really live?
    def sort_nodes_by_shortname(self):
        self.data.nodes = dict(
            sorted(self.data.nodes.items(), key=lambda item: item[1]["shortname"]))
