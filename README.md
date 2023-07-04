# Dwarf II TCP server

**NOTE: This is a work in progress. It's been cloudy, so I haven't tested this code yet.**

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

```
pip install -r requirements.txt
```

4. Copy `config.sample.py`, and rename it to `config.py`.

The `HOST` and `PORT` should be the same as those used in Stellarium Telescope Plugin.

Fill in your `LATITUDE` and `LONGITUDE`.

If you are using the Dwarf wifi, the `DWARF_IP` is 192.168.88.1. If you are using Dwarf II in STA mode, then get the IP for your Dwarf II.

`DEBUG = True` will print all the messages sent between Stellarium and Dwarf II. Set to `DEBUG = False`


5. Start server

```
python server.py
```

6. Select an object in Stellarium, and issue a slew command. The Dwarf II should move to that object.
