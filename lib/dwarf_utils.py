from lib.websockets_utils import connect_socket
import lib.dwarfII_api as d2
import config
import lib.my_logger as log
import proto.astro_pb2 as astro

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

def perform_goto(ra, dec, result_queue):

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
