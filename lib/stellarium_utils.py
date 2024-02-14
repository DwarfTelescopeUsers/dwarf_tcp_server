import struct
import time
import math

import lib.my_logger as my_logger

def process_ra_dec_int(ra_int, dec_int):
    h = ra_int
    d = math.floor(0.5 + dec_int * (360 * 3600 * 1000 / 4294967296.0))
    dec_sign = ""
    if d >= 0:
        if d > 90 * 3600 * 1000:
            d = 180 * 3600 * 1000 - d
            h += 0x80000000
        dec_sign = "+"
    else:
        if d < -90 * 3600 * 1000:
            d = -180 * 3600 * 1000 - d
            h += 0x80000000
        d = -d
        dec_sign = "-"

    h = math.floor(0.5 + h * (24 * 3600 * 10000 / 4294967296.0))
    h /= 10000
    ra_sec = h % 60
    h /= 60
    ra_min = h % 60
    h /= 60
    h %= 24

    d /= 1000
    dec_sec = d % 60
    d /= 60
    dec_min = d % 60
    d /= 60

    return {
        "ra": {"hour": math.floor(h), "minute": math.floor(ra_min), "second": ra_sec},
        "dec": {
            "dec_sign": dec_sign,
            "degree": math.floor(d),
            "minute": math.floor(dec_min),
            "second": dec_sec,
        },
    }

def process_ra_dec(ra_int, dec_int):
    data = process_ra_dec_int(ra_int, dec_int)
    ra = data["ra"]
    dec = data["dec"]
    ra_number = ra['hour'] + ra['minute'] / 60 + ra['second'] / 3600
    if dec_int >= 0:
      dec_number = dec['degree'] + dec['minute'] / 60 + dec['second'] / 3600
    else:
      dec_number = -(dec['degree'] + dec['minute'] / 60 + dec['second'] / 3600)

    return {
        "ra_number": ra_number,
        "dec_number": dec_number
    }


def format_ra_dec(ra_int, dec_int):
    data = process_ra_dec_int(ra_int, dec_int)
    ra = data["ra"]
    dec = data["dec"]
    ra_str = f"{ra['hour']}h {ra['minute']}m {'%.2f' % ra['second']}s"
    dec_str = (
        f"{dec['dec_sign']}{dec['degree']}° {dec['minute']}' {'%.2f' % dec['second']}\""
    )

    return {"ra": ra_str, "dec": dec_str}


def process_stellarium_data(raw_data):
    my_logger.debug("data from Stellarium >>", raw_data)
    try:
        data = struct.unpack("3iIi", raw_data)
        my_logger.debug("data from Stellarium >>", data)

        ra_int = data[3]
        dec_int = data[4]
        formatted_data = format_ra_dec(ra_int, dec_int)
        my_logger.debug("ra: " + formatted_data["ra"] + ", dec: " + formatted_data["dec"])

        data_number = process_ra_dec(ra_int, dec_int)
        ra_number = data_number["ra_number"]
        dec_number = data_number["dec_number"]
        my_logger.debug("ra: " + f"{ra_number}" + ", dec: " + f"{dec_number}")

        return {
            "ra_int": ra_int,
            "ra": formatted_data["ra"],
            "ra_number": ra_number,
            "dec_int": dec_int,
            "dec": formatted_data["dec"],
            "dec_number": dec_number,
        }

    except struct.error:
        # If a struct.error occurs, the data is not in the expected structure format
        my_logger.debug("data from Stellarium Mobile >>", raw_data)
        return False


def update_stellarium(ra_int, dec_int, connection):
    timestamp = math.floor(time.time())
    reply = struct.pack("3iIii", 24, 0, timestamp, ra_int, dec_int, 0)
    connection.send(reply)
