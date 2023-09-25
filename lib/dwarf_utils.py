from lib.websockets_utils import connect_socket
import lib.dwarfII_api as d2
import config
import lib.my_logger as log


def perform_goto(ra, dec):
    # Inverse LONGITUDE for DwarfII !!!!!!!
    payload = d2.goto_target(config.LATITUDE, - config.LONGITUDE, ra, dec)

    response = connect_socket(payload)

    if response: 

      if response["interface"] == payload["interface"]:
        if response["code"] == 0:
            log.debug("Goto success")
            return "ok"
        elif response["code"] == -45:
            log.error("Target below horizon")
        elif response["code"] == -46:
            log.error("Goto or correction bump limit")
        else:
            log.error("Error:", response)
      else:
        log.error("Dwarf API:", response)
    else:
        log.error("Dwarf API:", "Dwarf II not connected")


def perform_camera_status():
    payload = d2.cameraWorkingState()
    connect_socket(payload)
