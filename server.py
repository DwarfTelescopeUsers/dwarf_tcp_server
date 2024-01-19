import socket
import threading
from queue import Queue

from datetime import datetime
from zoneinfo import ZoneInfo

import config
import lib.my_logger as my_logger
from lib.stellarium_utils import process_stellarium_data, update_stellarium
from lib.dwarf_utils import perform_goto

# Convert Deg to 
def process_deg_dec(deg_dec):
    deg_sign = ""

    if deg_dec >= 0:
        deg_sign = "+"
    else:
        deg_sign = "-"
        deg_dec = -deg_dec

    d = int(deg_dec)
    my_logger.debug(f"process_deg_dec: {deg_sign}{deg_dec}<->{d}")

    dec_min = int((deg_dec - d) * 60 )
    dec_sec = int((deg_dec - d - (dec_min / 60))*3600)

    return {
            "deg_sign": deg_sign,
            "degree": d,
            "minute": dec_min,
            "second": dec_sec,
    }


# Create a Queue to pass the result from the thread to the main program
result_queue = Queue()
dwarf_ra_deg = 0
dwarf_dec_deg = 0
dwarf_goto_thread_started = False

# Create a thread and pass variables to it
dwarf_goto_thread = False

nbDeconnect = 10

while True:

    my_logger.debug(f"Waiting Connection to Stellarium : {config.HOST}")

    # create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # ensure we can quickly restart server
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # set host and port
    sock.bind((config.HOST, config.PORT))
    # set number of client that can be queued
    sock.listen(5)

    while True:
        # create new socket to interact with client
        new_socket, addr = sock.accept()
        my_logger.debug(f"Connected by {addr}")

        raw_data = new_socket.recv(1024)
        if not raw_data:
            break

        # process data from Stellarium PC to get RA/Dec
        data = process_stellarium_data(raw_data)

        if (data): # For Stellarium PC
            # send goto command to DWARF II
            if hasattr(config, 'VERSION_API'):
                if (config.VERSION_API == 1):
                    result = perform_gotoV1(data["ra_number"], data["dec_number"], result_queue)
                else:
                    result = perform_goto(data["ra_number"], data["dec_number"], result_queue)
            else:
                result = perform_goto(data["ra_number"], data["dec_number"], result_queue)

            # add DWARF II to Stellarium's sky map
            if result == "ok":
                update_stellarium(data["ra_int"], data["dec_int"], new_socket)

            new_socket.close()

        else: # For Stellarium Mobile Plus simulate Telescope Nexstar
            location = ""
            datetoday = ""
            goto_data = b'1B4A735F,3F7A6B85#' # Init to Polaris Position
            goto = False
            ra_deg = 0
            dec_deg = 0

            while True:
                send_data = b'##'
                if (raw_data == b'Ka'):
                    send_data = b'a#'
                if (raw_data == b'V'):  # Version
                    send_data = b'\x02\x06#'
                if (raw_data == b'P\x01\x10\xfe\x00\x00\x00\x02'):  # Version AZM/ RA motor
                    send_data = b'\x02\x06#'
                if (raw_data == b'P\x01\x11\xfe\x00\x00\x00\x02'):  # Version Alt/ DEC motor
                    send_data = b'\x02\x06#'
                if (raw_data == b'm'):  # Model
                    send_data = b'\x10#'
                if (raw_data == b't'):  # Tracking Mode
                    send_data = b'\x00#' # b'\x02#
                if (raw_data == b'L'):  # Is GOTO
                    if (goto):
                        send_data = b'1#'
                    else:
                        send_data = b'0#'
                if (raw_data == b'J'):  # Is Align
                    send_data = b'\x01#'  
                if (raw_data == b'e'):  # Position 
                    send_data = goto_data

                if (raw_data == b'h'):  # Send Time
                    today = datetime.now()
                    # Get Local Timezone from Config
                    try:
                        local_timezone = config.TIME_ZONE
                    except AttributeError as e:
                        local_timezone = "UTC"
                        my_logger.debug(f"No TimeZone defined in config, UTC used")

                    # Show Local Timezone
                    my_logger.debug(f"Local Timezone:", local_timezone)
                    date_GMTDST = datetime(today.year, today.month, today.day, tzinfo=ZoneInfo(local_timezone))
                    # Get GMT
                    gmt = int(date_GMTDST.utcoffset().total_seconds() // 3600)
                    if (gmt < 0):
                        gmt = 256 - gmt
                    # Get DST
                    dst_active = 1
                    if (int(date_GMTDST.dst().total_seconds()) == 0):
                        dst_active = 0
                    my_logger.debug(f"Local Date Time :", today, gmt, dst_active)

                    # today_hexa = f"{hex(today.hour)[2:]}{hex(today.minute)[2:]}{hex(today.second)[2:]}{hex(today.month)[2:]}{hex(today.day)[2:]}{hex(today.year-2000)[2:]}{hex(gmt)[2:]}{hex(dst_active)[2:]}"
                    today_hexa = f"{today.hour:02x}{today.minute:02x}{today.second:02x}{today.month:02x}{today.day:02x}{today.year-2000:02x}{gmt:02x}{dst_active:02x}"
                    my_logger.debug(f"Date Time hexa: ", today_hexa)
                    send_data = bytes.fromhex(today_hexa) + b'#'  

                if (raw_data[0] == ord('H')): #  Get Time
                    datetoday = raw_data[1:]
                    Time = f"{raw_data[1]}H{raw_data[2]}M{raw_data[3]}S"
                    Date = f"{raw_data[4]}/{raw_data[5]}/20{raw_data[6]}\""
                    GMT  = f"GMT +{raw_data[7]}"
                    my_logger.debug(f"Date Time GMT :", GMT)
                    if (int(raw_data[7]) <= 127):
                        GMT  = f"GMT +{raw_data[7]}"
                    else:
                        GMT  = f"GMT -{256-raw_data[7]}"
                    DST  = ""
                    if (raw_data[8] == 1):
                        DST  = "DST"
                    my_logger.debug(f"Date Time :", Date, Time, GMT, DST)
                    send_data = b'#'  

                if (raw_data == b'w'):  # send Local Location
                    send_data = b'/\x13,\x00\x01),\x01'
                    if (location):
                        send_data = location + b'#'  
                    # Get Local Location from Config
                    try:
                        Latitude = config.LATITUDE
                        Longitude = config.LONGITUDE
                        my_logger.debug(f"Config Local Location:", Latitude, Longitude)
                    except AttributeError as e:
                        local_timezone = "UTC"
                        my_logger.debug(f"No Local Location Info in config, send Location from phone")
                        if (location):
                            send_data = location + b'#'  

                    data_Lat = process_deg_dec(Latitude)
                    Lat_NS = 0
                    if (data_Lat['deg_sign'] == "-"):
                        Lat_NS = 1
                    
                    data_Lon = process_deg_dec(Longitude)
                    Lon_WE = 0
                    if (data_Lon['deg_sign'] == "-"):
                        Lon_WE = 1
                    
                    str_lattitude = f"{data_Lat['degree']}°{data_Lat['minute']}'{data_Lat['second']}\""
                    if (data_Lat['deg_sign'] == "+"):
                        str_lattitude  += "N"
                    else:
                        str_lattitude  += "S"
                    
                    str_longitude = f"{data_Lon['degree']}°{data_Lon['minute']}'{data_Lon['second']}\""
                    if (data_Lon['deg_sign'] == "-"):
                        str_longitude  += "W"
                    else:
                        str_longitude  += "E"
                    my_logger.debug(f"Local Location:", str_lattitude, str_longitude)

                    data_location_hexa = f"{data_Lat['degree']:02x}{data_Lat['minute']:02x}{data_Lat['second']:02x}{Lat_NS:02x}{data_Lon['degree']:02x}{data_Lon['minute']:02x}{data_Lon['second']:02x}{Lon_WE:02x}"
                    my_logger.debug(f"Local Location hexa: ", data_location_hexa)
                    send_data = bytes.fromhex(data_location_hexa) + b'#'  

                if (raw_data[0] == ord('W')):  # get Location
                    location = raw_data[1:]
                    lattitude = f"{raw_data[1]}°{raw_data[2]}'{raw_data[3]}\""
                    if (raw_data[4] == 0):
                        lattitude  += "N"
                    else:
                        lattitude  += "S"
                    longitude = f"{raw_data[5]}°{raw_data[6]}'{raw_data[7]}\""
                    if (raw_data[8] == 0):
                        longitude  += "E"
                    else:
                        longitude  += "W"
                    my_logger.debug(f"Location:", lattitude, longitude)
                    send_data = b'#'  

                # GOTO Command
                if (raw_data[0] == ord('r')):
                    my_logger.debug(f"Receive Goto Command : {raw_data}")
                    my_logger.debug(f"Receive Goto Command : RA {raw_data[1:7]}")
                    my_logger.debug(f"Receive Goto Command : DEC {raw_data[10:16]}")
                    ra_data =  int(raw_data[1:7], base=16)
                    if (ra_data < 0):
                        ra_data = 16777216 + ra_data
                    ra_deg = (ra_data / 16777216) * 360 / 15
                    my_logger.debug(f"Decode Ra:{ra_deg}")
                    dec_data =  int(raw_data[10:16], base=16)
                    dec_deg = (dec_data / 16777216) * 360
                    my_logger.debug(f"Decode Dec:{dec_deg}")
                    if (dec_deg > 180):
                        dec_deg = dec_deg - 360
                    my_logger.debug(f"Receive Goto Command : Ra:{ra_deg} Dec:{dec_deg}")

                    if (dwarf_goto_thread_started):
                        my_logger.debug(f"Receive Goto Command : Goto is still Processing Wait...")
                    else:
                        goto = True

                        # start thread goto command to DWARF II
                        dwarf_goto_thread_started = True
                        dwarf_ra_deg = ra_deg;
                        dwarf_dec_deg = dec_deg;
                        if (config.VERSION_API == 1):
                            dwarf_goto_thread = threading.Thread(target=perform_gotoV1, args=(dwarf_ra_deg, dwarf_dec_deg, result_queue))
                        else:
                            dwarf_goto_thread = threading.Thread(target=perform_goto, args=(dwarf_ra_deg, dwarf_dec_deg, result_queue))
                        dwarf_goto_thread.start()

                    send_data = b'#'  

                my_logger.debug(f"Sending ...", send_data)
                new_socket.send(send_data)

                raw_data = new_socket.recv(1024)
                if not raw_data:
                   break

                my_logger.debug("data from Stellarium >>", raw_data)

                if goto:
                    if not(dwarf_goto_thread.is_alive()):
                        my_logger.debug("End of Dwarf Goto")
                        dwarf_goto_thread_started = False
                        goto = False
                        # Retrieve the result from the Queue
                        result = result_queue.get()

                        # add DWARF II to Stellarium's sky map
                        if result == "ok":
                            goto_data = raw_data[1:]

                        # Create a thread and pass variables to it for next time
                        dwarf_goto_thread = False

    my_logger.debug(f"Disconnected from Stellarium : {addr}")

    nbDeconnect -= 1

    if (nbDeconnect <= 0):
        restart = input("Restart? [Y/n]")
    
        if restart != "Y" and restart != "y":
            my_logger.debug("End of Server")
            break;
        else:
            nbDeconnect = 3
