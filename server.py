import socket

import config
import lib.my_logger as my_logger
from lib.stellarium_utils import process_stellarium_data, update_stellarium
from lib.dwarf_utils import perform_goto

let nbDeconnect = 3

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

        # process data from Stellarium to get RA/Dec
        data = process_stellarium_data(raw_data)

        # send goto command to DWARF II
        result = perform_goto(data["ra_number"], data["dec_number"])

        # add DWARF II to Stellarium's sky map
        if result == "ok":
            update_stellarium(data["ra_int"], data["dec_int"], new_socket)

        new_socket.close()

    my_logger.debug(f"Disconnected from Stellarium : {addr}")

    nbDeconnect -= 1

    if (nbDeconnect <= 0):
        restart = input("Restart? [Y/n]")
    
        if restart != "Y" and restart != "y":
            my_logger.debug("End of Server")
            break;
        else:
            nbDeconnect = 3