# Dwarf II TCP server

This software lets you send goto commands to the Dwarf II using Stellarium's Telescope Control.

Requires:
- Python
- Stellarium with Telescope Control plugin
- Dwarf II

## Details

This software setups up a TCP server. When you select an object Stellarium, and execute a slew command, Stellarium will send data about the object to this server. This server will take the right acension and declination data, and send a goto command to the Dwarf API via websockets.


## Instructions

1. Enable the Telescope Control plugin in Stellarium, and add a new telescope. Set "Telescope controlled by" to "External software or a remote computer". You can use the default settings for "Host" and "TCP port" for "Connection settings". Click 'OK' to create telescope. Select the newly added telescope, and click "Connect"

2. Download this repo

3. Install libraries

On Linux, Mac or WSL for Windows : 

```
pip install -r requirements.txt
```

On Windows : 

you can install Python 3.11 (search on Microsoft Store)
open a command prompt on the directory and do :  

```
python3 -m pip install -r requirements.txt
```

4. Copy `config.sample.py`, and rename it to `config.py`.

The `HOST` and `PORT` should be the same as those used in Stellarium Telescope Plugin.

Fill in your `LATITUDE` and `LONGITUDE`  (LONGITUDE is negative west of Greenwich)

Add also your `TIMEZONE`, it's need when you are using the Stellarium Mobile App

If you are using the Dwarf wifi, the `DWARF_IP` is 192.168.88.1. If you are using Dwarf II in STA mode, then get the IP for your Dwarf II.

`DEBUG = True` will print all the messages sent between Stellarium and Dwarf II. Set to `DEBUG = False`


5. Start server

```
python server.py
```

On Windows : 

```
python3 server.py
```

6. Start the dwarf II and use the mobile app and go to Astro Mode and do the calibration

7. Select an object in Stellarium, and issue a slew command. (shortcut for Windows is Alt + number, See Stellarium documentation, Command + number for Mac). The Dwarf II should move to that object.

8. You can also use the Stellarium Plus Mobile App with the remote Telescopte function, Select an object in Stellarium, and issue a goto command with the remote control. The Dwarf II should move to that object.

**NOTE: If the server disconnects from Stellarium, You can try reconnect on the cmd window by typing Y otherwise the program will stop **
