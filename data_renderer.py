#!/usr/bin/env python3

import asyncio
import json
import logging
import os

from encoders import _JSONEncoder


class DataRenderer:
    def __init__(self, config, data):
        self.config = config
        self.data = data

    async def render(self):
        await asyncio.to_thread(self._render)

    def _render(self):
        self.save_file("chat.json", self.data.chat)
        logging.info(
            f"Saved {len(self.data.chat['channels']['0']['messages'])} chat messages to file ({self.config['paths']['data']}/chat.json)")

        nodes = {}
        for id, node in self.data.nodes.items():
            if id.startswith('!'):
                id = id.replace('!', '')
            if len(id) != 8:  # 8 hex chars required, if not, we abandon it
                continue
            nodes[id] = node

        self.save_file("nodes.json", nodes)
        logging.info(
            f"Saved {len(nodes)} nodes to file ({self.config['paths']['data']}/nodes.json)")

        self.save_file("telemetry.json", self.data.telemetry)
        logging.info(
            f"Saved {len(self.data.telemetry)} telemetry to file ({self.config['paths']['data']}/telemetry.json)")

        self.save_file("traceroutes.json", self.data.traceroutes)
        logging.info(
            f"Saved {len(self.data.traceroutes)} traceroutes to file ({self.config['paths']['data']}/traceroutes.json)")

    def save_file(self, filename, data):
        logging.info(f"Saving {filename}")
        with open(f"{self.config['paths']['data']}/{filename}.swp", "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, sort_keys=True, cls=_JSONEncoder)

        os.replace(f"{self.config['paths']['data']}/{filename}.swp",
                   f"{self.config['paths']['data']}/{filename}")
