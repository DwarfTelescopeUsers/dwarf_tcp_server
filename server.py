import socket

import config
import lib.my_logger as my_logger
from lib.stellarium_utils import process_stellarium_data
from lib.dwarf_utils import perform_goto

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

    data = process_stellarium_data(raw_data)
    new_socket.close()
