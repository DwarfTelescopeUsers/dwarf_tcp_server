from websockets.sync.client import connect
import config
import json

import lib.my_logger as my_logger
from lib.dwarfII_api import ws_uri


def connect_socket(payload):
    try:
        with connect(ws_uri(config.DWARF_IP)) as websocket:
            my_logger.debug("data to API >>", json.dumps(payload, indent=2))
            websocket.send(json.dumps(payload))

            message = websocket.recv()
            return json.loads(message)
    except TimeoutError:
        my_logger.error("Could not connect to websocket")
