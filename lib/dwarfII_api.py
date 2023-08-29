import datetime

startGotoCmd = 11203
statusWorkingStateTelephotoCmd = 10022
telephotoCamera = 0


def ws_uri(dwarf_ip):
    return f"ws://{dwarf_ip}:9900"


def now():
    return str(datetime.datetime.now()).split(".")[0]

def nowUTC():
    return str(datetime.datetime.utcnow()).split(".")[0]


def nowLocalFileName():
  return datetime.datetime.today().strftime('%Y%m%d%H%M%S')

def goto_target(latitude, longitude, rightAscension, declination, planet=None):
    options = {
        "interface": startGotoCmd,
        "camId": telephotoCamera,
        "lon": longitude,
        "lat": latitude,
        "date": nowUTC(),
        "path": "DWARF_GOTO_" + nowLocalFileName(),
    }

    if planet is not None:
        options["planet"] = planet
    else:
        options["ra"] = rightAscension
        options["dec"] = declination

    return options


def cameraWorkingState():
    return {
        "interface": statusWorkingStateTelephotoCmd,
        "camId": telephotoCamera,
    }
