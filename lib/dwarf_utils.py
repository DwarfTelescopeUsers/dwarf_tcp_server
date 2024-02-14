from lib.websockets_utils import connect_socket
import lib.dwarfII_api as d2
import config
import lib.my_logger as log
import proto.astro_pb2 as astro
import proto.system_pb2 as system
import time
import math

def perform_gotoV1(ra, dec, result_queue):
    # Inverse LONGITUDE for DwarfII !!!!!!!
    payload = d2.goto_target(config.LATITUDE, - config.LONGITUDE, ra, dec)

    response = connect_socketV1(payload)

    if response: 

      if response["interface"] == payload["interface"]:
        if response["code"] == 0:
            log.debug("Goto success")
            result_queue.put("ok")
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

    result_queue.put(False)

# Add an number to target Stellarium to have a different target name each time
global id_target
id_target = 0

global do_time
do_time = False

global do_timezone
do_timezone = False


def perform_goto(ra, dec, result_queue):

    global do_time
    global do_timezone

    if (not do_time):
        perform_time()
        do_time = True

    if (not do_time):
        perform_timezone()
        do_timezone = True

    # Add an number to target Stellarium to have a different target name each time
    global id_target
    id_target += 1

    if (id_target >= 10):
        id_target = 1

    # GOTO
    module_id = 3  # MODULE_ASTRO
    type_id = 0; #REQUEST

    ReqGotoDSO_message = astro.ReqGotoDSO()
    ReqGotoDSO_message.ra = ra
    ReqGotoDSO_message.dec = dec
    ReqGotoDSO_message.target_name = f"Stellarium_{id_target}"

    command = 11002 #CMD_ASTRO_START_GOTO_DSO
    response = connect_socket(ReqGotoDSO_message, command, type_id, module_id)

    if response is not False: 

      if response == "ok":
          log.debug("Goto success")
          result_queue.put("ok")
          return "ok"
      else:
          log.error("Error:", response)
    else:
        log.error("Dwarf API:", "Dwarf II not connected")

    result_queue.put(False)

def perform_time():

    # SET TIME
    module_id = 4  # MODULE_SYSTEM
    type_id = 0; #REQUEST

    ReqSetTime_message = system.ReqSetTime()
    ReqSetTime_message.timestamp = math.floor(time.time())

    command = 13000 #CMD_SYSTEM_SET_TIME
    response = connect_socket(ReqSetTime_message, command, type_id, module_id)

    if response is not False: 

      if response == 0:
          log.debug("Set Time success")
          return True
      else:
          log.error("Error:", response)
    else:
        log.error("Dwarf API:", "Dwarf II not connected")

    return False

def perform_timezone():

    # SET TIMEZONE
    module_id = 4  # MODULE_SYSTEM
    type_id = 0; #REQUEST

    ReqSetTimezone_message = system.ReqSetTimezone()
    ReqSetTimezone_message.timezone = read_timezone()

    command = 13001 #CMD_SYSTEM_SET_TIME_ZONE
    response = connect_socket(ReqSetTimezone_message, command, type_id, module_id)

    if response is not False: 

      if response == 0:
          log.debug("Set TimeZone success")
          return True
      else:
          log.error("Error:", response)
    else:
        log.error("Dwarf API:", "Dwarf II not connected")

    return False

