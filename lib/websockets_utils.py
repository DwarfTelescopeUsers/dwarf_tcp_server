import logging
import websockets
import asyncio
import json
import gzip
import config
import proto.protocol_pb2 as protocol
import proto.notify_pb2 as notify
import proto.astro_pb2 as astro
import proto.system_pb2 as system
import proto.camera_pb2 as camera
# in notify
import proto.base_pb2 as base__pb2

import lib.my_logger as my_logger

def ws_uri(dwarf_ip):
    return f"ws://{dwarf_ip}:9900"

def getErrorCodeValueName(ErrorCode):

    try:
        ValueName = protocol.ErrorCodeAstro.Name(ErrorCode)
    except ValueError:
        ValueName =""
        pass
    return ValueName

def getAstroCMDName(AstroCMDCode):

    try:
        ValueName = protocol.AstroCMD.Name(AstroCMDCode)
    except ValueError:
        ValueName =""
        pass
    return ValueName

def getAstroStateName(AstroStateCode):

    try:
        ValueName = notify.AstroState.Name(AstroStateCode)
    except ValueError:
        ValueName =""
        pass
    return ValueName

class StopClientException(Exception):
    pass

# new version protobuf enabled
# use a Class
class WebSocketClient:
    def __init__(self, uri, client_id, message, command, type_id, module_id, ping_interval_task=5):
        self.websocket = False
        self.result = False
        self.uri = uri
        self.message = message
        self.command = command
        self.target_name = ""
        self.type_id = type_id
        self.module_id = module_id
        self.client_id = client_id
        self.ping_interval_task = ping_interval_task
        self.ping_task = None
        self.receive_task = None
        self.abort_tasks = None
        self.abort_timeout = 90
        self.stop_task = asyncio.Event()
        self.wait_pong = False

        # TEST_CALIBRATION : Test Calibration Packet or Goto Packet
        # Test Mode : Calibration Packet => TEST_CALIBRATION = True
        # Production Mode GOTO Packet => TEST_CALIBRATION = False (default)
        self.modeCalibration = False

        if hasattr(config, 'TEST_CALIBRATION'):
            if(config.TEST_CALIBRATION):
                self.modeCalibration = True

    async def abort_tasks_timeout(self, timeout):

        try:
            count = 0
            self.abort_timeout = timeout
            await asyncio.sleep(0.02)
            while not self.stop_task.is_set() and count < self.abort_timeout:
                await asyncio.sleep(1)
                count += 1
        except Exception as e:
            # Handle other exceptions
            print(f"Timeout: Unhandled exception: {e}")
        finally:
            # Perform cleanup if needed
            if (not self.stop_task.is_set()):
                self.stop_task.set()
            await asyncio.sleep(0.02)
            print("TERMINATING TIMEOUT function.")

    async def send_ping_periodically(self):
        if not self.websocket:
            print("Error No WebSocket in send_ping_periodically")
            self.stop_task.set()

        try:
            await asyncio.sleep(2)
            while not self.stop_task.is_set():
                if self.websocket.state != websockets.protocol.OPEN:
                    print("WebSocket connection is not open.")
                    self.stop_task.set()
                elif (not self.wait_pong):
                    # Adjust the interval based on your requirements
                    print("Sent a PING frame")

                    # Python by defaut sends a frame OP_CODE Ping with 4 bytes
                    # The dwarf II respond by a frame OP_CODE Pong with no data
                    await self.websocket.ping("")
                    await self.websocket.send("ping")
                    # Signal to Receive to Wait the Pong Frame
                    self.wait_pong = True
                    await asyncio.sleep(self.ping_interval_task)
                else:
                    await asyncio.sleep(1)
            await asyncio.sleep(0.02)

        except websockets.ConnectionClosedOK as e:
            print(f'Ping: ConnectionClosedOK', e)
        except websockets.ConnectionClosedError as e:
            print(f'Ping: ConnectionClosedError', e)
        except asyncio.CancelledError:
            print("Ping Cancelled.")
        except Exception as e:
            # Handle other exceptions
            print(f"Ping: Unhandled exception: {e}")
            if (not self.stop_task.is_set()):
                self.stop_task.set()
            await asyncio.sleep(1)
        finally:
            # Perform cleanup if needed
            print("TERMINATING PING function.")

    async def receive_messages(self):
        if not self.websocket:
            print("Error No WebSocket in receive_messages")
            self.stop_task.set()

        try:
            await asyncio.sleep(2)
            while not self.stop_task.is_set() or self.wait_pong:
                await asyncio.sleep(0.02)
                print("Wait for frames")

                if self.websocket.state != websockets.protocol.OPEN:
                    print("WebSocket connection is not open.")
                    self.wait_pong = False
                    self.stop_task.set()
                else:
                    message = await self.websocket.recv()
                    if (message):
                        if isinstance(message, str):
                            print("Receiving...")
                            print(message)
                            if (message =="pong"):
                                 self.wait_pong = False
                        elif isinstance(message, bytes):
                            print("------------------")
                            print("Receiving...  data")

                            WsPacket_message = base__pb2.WsPacket()
                            WsPacket_message.ParseFromString(message)
                            my_logger.debug(f"receive cmd >> {WsPacket_message.cmd} type >> {WsPacket_message.type}")
                            my_logger.debug(f">> {getAstroCMDName(WsPacket_message.cmd)}")
                            my_logger.debug(f"msg data len is >> {len(WsPacket_message.data)}")
                            print("------------------")

                            # CMD_NOTIFY_WS_HOST_SLAVE_MODE = 15223; // Leader/follower mode notification
                            if (WsPacket_message.cmd==protocol.CMD_NOTIFY_WS_HOST_SLAVE_MODE):
                                ResNotifyHostSlaveMode_message = notify.ResNotifyHostSlaveMode()
                                ResNotifyHostSlaveMode_message.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_NOTIFY_WS_HOST_SLAVE_MODE")
                                my_logger.debug(f"receive Host/Slave data >> {ResNotifyHostSlaveMode_message.mode}")

                                # Host = 0 Slave = 1
                                if (ResNotifyHostSlaveMode_message.mode == 1):
                                    my_logger.debug("SLAVE_MODE >> EXIT")
                                    # Signal the abort_tasks_timeout functions to stop in 15 s
                                    if (self.abort_timeout > 15 ):
                                        self.abort_timeout = 15
                                    self.result = "Error SLAVE MODE"
                                    await asyncio.sleep(1)
                                    print("Error SLAVE MODE detected")
                                else:
                                    print("Continue Decoding CMD_NOTIFY_WS_HOST_SLAVE_MODE")

                            # CMD_CAMERA_TELE_GET_SYSTEM_WORKING_STATE = 10039; // // Get the working status of the whole machine
                            elif (WsPacket_message.cmd==protocol.CMD_CAMERA_TELE_GET_SYSTEM_WORKING_STATE):
                                ComResponse_message = base__pb2.ComResponse()
                                ComResponse_message.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_CAMERA_TELE_GET_SYSTEM_WORKING_STATE")
                                my_logger.debug(f"receive code data >> {ComResponse_message.code}")
                                my_logger.debug(f">> {getErrorCodeValueName(ComResponse_message.code)}")

                                # NO_ERROR = 0; // No Error
                                if (ComResponse_message.code != protocol.NO_ERROR):
                                    my_logger.debug(f"Error GET_SYSTEM_WORKING_STATE {ComResponse_message.code} >> EXIT")
                                    # Signal the ping and receive functions to stop
                                    self.stop_task.set()
                                    self.result = "ok"
                                    await asyncio.sleep(5)
                                    print("Error CAMERA_TELE_GET_SYSTEM_WORKING_STATE CODE " + ComResponse_message.code)
                                else:
                                    print("Continue OK CMD_CAMERA_TELE_GET_SYSTEM_WORKING_STATE")

                            # CMD_NOTIFY_STATE_ASTRO_CALIBRATION = 15210; // Astronomical calibration status
                            elif (WsPacket_message.cmd==protocol.CMD_NOTIFY_STATE_ASTRO_CALIBRATION):
                                ResNotifyStateAstroCalibration_message = notify.ResNotifyStateAstroCalibration()
                                ResNotifyStateAstroCalibration_message.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_NOTIFY_STATE_ASTRO_CALIBRATION")
                                my_logger.debug(f"receive notification data >> {ResNotifyStateAstroCalibration_message.state}")
                                my_logger.debug(f">> {getAstroStateName(ResNotifyStateAstroCalibration_message.state)}")
                                my_logger.debug(f"receive notification times >> {ResNotifyStateAstroCalibration_message.plate_solving_times}")

                                # ASTRO_STATE_IDLE = 0; // Idle state Only when Success
                                if (ResNotifyStateAstroCalibration_message.state == notify.ASTRO_STATE_IDLE):
                                    my_logger.debug("ASTRO CALIBRATION OK >> EXIT")
                                    # Signal the ping and receive functions to stop
                                    self.stop_task.set()
                                    self.result = "ok"
                                    await asyncio.sleep(5)
                                    print("Success ASTRO CALIBRATION OK")
                                else:
                                    print("Continue Decoding CMD_NOTIFY_STATE_ASTRO_CALIBRATION")

                            # CMD_NOTIFY_STATE_ASTRO_GOTO = 15211; // Astronomical GOTO status
                            elif (WsPacket_message.cmd==protocol.CMD_NOTIFY_STATE_ASTRO_GOTO):
                                ResNotifyStateAstroGoto_message = notify.ResNotifyStateAstroGoto()
                                ResNotifyStateAstroGoto_message.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_NOTIFY_STATE_ASTRO_GOTO")
                                my_logger.debug(f"receive notification data >> {ResNotifyStateAstroGoto_message.state}")
                                my_logger.debug(f">> {getAstroStateName(ResNotifyStateAstroGoto_message.state)}")

                            # CMD_NOTIFY_STATE_ASTRO_TRACKING = 15212; // Astronomical tracking status
                            elif (WsPacket_message.cmd==protocol.CMD_NOTIFY_STATE_ASTRO_TRACKING):
                                ResNotifyStateAstroGoto_message = notify.ResNotifyStateAstroTracking()
                                ResNotifyStateAstroGoto_message.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_NOTIFY_STATE_ASTRO_TRACKING")
                                my_logger.debug(f"receive notification data >> {ResNotifyStateAstroGoto_message.state}")
                                my_logger.debug(f">> {getAstroStateName(ResNotifyStateAstroGoto_message.state)}")
                                my_logger.debug(f"receive notification target_name >> {ResNotifyStateAstroGoto_message.target_name}")

                                # ASTRO_STATE_RUNNING = 1; // Running 
                                # Can be sending during CMD_CAMERA_TELE_GET_SYSTEM_WORKING_STATE
                                # DSO or STELLAR
                                if ((self.command == protocol.CMD_ASTRO_START_GOTO_DSO) and ResNotifyStateAstroGoto_message.state == notify.ASTRO_STATE_RUNNING and ResNotifyStateAstroGoto_message.target_name == self.target_name):
                                    my_logger.debug("ASTRO GOTO : SAME CMD AND TARGET")
                                    my_logger.debug("ASTRO GOTO OK TRACKING >> EXIT")
                                    # Signal the ping and receive functions to stop
                                    self.stop_task.set()
                                    self.result = "ok"
                                    await asyncio.sleep(5)
                                    print("Success ASTRO DSO GOTO TRACKING START")

                                if ((self.command == protocol.CMD_ASTRO_START_GOTO_SOLAR_SYSTEM) and ResNotifyStateAstroGoto_message.state == notify.ASTRO_STATE_RUNNING and ResNotifyStateAstroGoto_message.target_name == self.target_name):
                                    my_logger.debug("ASTRO GOTO : SAME CMD AND TARGET")
                                    my_logger.debug("ASTRO GOTO OK TRACKING >> EXIT")
                                    # Signal the ping and receive functions to stop
                                    self.stop_task.set()
                                    self.result = "ok"
                                    await asyncio.sleep(5)
                                    print("Success ASTRO SOLAR GOTO TRACKING START")

                            # CMD_ASTRO_START_CALIBRATION = 11000; // Start calibration
                            elif (WsPacket_message.cmd==protocol.CMD_ASTRO_START_CALIBRATION):
                                ComResponse = base__pb2.ComResponse()
                                ComResponse.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_ASTRO_START_CALIBRATION")
                                my_logger.debug(f"receive code data >> {ComResponse.code}")
                                my_logger.debug(f">> {getErrorCodeValueName(ComResponse.code)}")

                                # CODE_ASTRO_CALIBRATION_FAILED = -11504; // Calibration failed
                                if (ComResponse.code == -11504):
                                    my_logger.debug("Error CALIBRATION >> EXIT")
                                    # Signal the ping and receive functions to stop
                                    self.stop_task.set()
                                    self.result = protocol.CODE_ASTRO_CALIBRATION_FAILED
                                    await asyncio.sleep(5)
                                    print("Error CALIBRATION CODE_ASTRO_CALIBRATION_FAILED")

                            # CMD_SYSTEM_SET_TIME = 13000; // Set the system time
                            elif (WsPacket_message.cmd==protocol.CMD_SYSTEM_SET_TIME):
                                ComResponse = base__pb2.ComResponse()
                                ComResponse.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_SYSTEM_SET_TIME")
                                my_logger.debug(f"receive code data >> {ComResponse.code}")
                                my_logger.debug(f">> {getErrorCodeValueName(ComResponse.code)}")

                                # Signal the ping and receive functions to stop
                                self.stop_task.set()
                                self.result = ComResponse.code
                                await asyncio.sleep(5)
                                if (ComResponse.code == protocol.CODE_SYSTEM_SET_TIME_FAILED):
                                    print("Error CMD_SYSTEM_SET_TIME")
                                else:
                                    print("OK CMD_SYSTEM_SET_TIME")

                            # CMD_SYSTEM_SET_TIME_ZONE = 13001; // Set the time zone
                            elif (WsPacket_message.cmd==protocol.CMD_SYSTEM_SET_TIME_ZONE):
                                ComResponse = base__pb2.ComResponse()
                                ComResponse.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_SYSTEM_SET_TIME_ZONE")
                                my_logger.debug(f"receive code data >> {ComResponse.code}")
                                my_logger.debug(f">> {getErrorCodeValueName(ComResponse.code)}")

                                # Signal the ping and receive functions to stop
                                self.stop_task.set()
                                self.result = ComResponse.code
                                await asyncio.sleep(5)
                                if (ComResponse.code == protocol.CODE_SYSTEM_SET_TIMEZONE_FAILED):
                                    print("Error CMD_SYSTEM_SET_TIME_ZONE")
                                else:
                                    print("OK CMD_SYSTEM_SET_TIME_ZONE")

                            # CMD_ASTRO_START_GOTO_DSO = 11002; // Start GOTO Deep Space Object
                            elif (WsPacket_message.cmd==protocol.CMD_ASTRO_START_GOTO_DSO):
                                ComResponse_message = base__pb2.ComResponse()
                                ComResponse_message.ParseFromString(WsPacket_message.data)

                                print("Decoding CMD_ASTRO_START_GOTO_DSO")
                                my_logger.debug(f"receive data >> {ComResponse_message.code}")
                                my_logger.debug(f">> {getErrorCodeValueName(ComResponse_message.code)}")

                                if (ComResponse_message.code != protocol.NO_ERROR):
                                    my_logger.debug(f"Error GOTO {ComResponse_message.code} >> EXIT")
                                    # Signal the ping and receive functions to stop
                                    self.stop_task.set()
                                    self.result = ComResponse_message.code
                                    await asyncio.sleep(5)
                                    if (ComResponse_message.code == protocol.CODE_ASTRO_GOTO_FAILED):
                                        print("Error GOTO CODE_ASTRO_GOTO_FAILED")
                                    elif (ComResponse_message.code == protocol.CODE_STEP_MOTOR_LIMIT_POSITION_WARNING):
                                        print("Error GOTO CODE_STEP_MOTOR_LIMIT_POSITION_WARNING")
                                    elif (ComResponse_message.code == protocol.CODE_STEP_MOTOR_LIMIT_POSITION_HITTED):
                                        print("Error GOTO CODE_STEP_MOTOR_LIMIT_POSITION_HITTED")
                                    else:
                                        print("Error GOTO CODE " + ComResponse_message.code)
                            # Unknown
                            elif (WsPacket_message.cmd != self.command):
                                if( WsPacket_message.type == 0):
                                    print("Get Request Frame")
                                if( WsPacket_message.type == 1):
                                    print("Decoding Response Request Frame")
                                    ComResponse_message = base__pb2.ComResponse()
                                    ComResponse_message.ParseFromString(WsPacket_message.data)

                                    my_logger.debug(f"receive request response data >> {ComResponse_message.code}")
                                    my_logger.debug(f">> {getErrorCodeValueName(ComResponse_message.code)}")

                                if( WsPacket_message.type == 2):
                                    print("Decoding Notification Frame")
                                    ResNotifyStateAstroGoto_message = notify.ResNotifyStateAstroGoto()
                                    ResNotifyStateAstroGoto_message.ParseFromString(WsPacket_message.data)

                                    my_logger.debug(f"receive notification data >> {ResNotifyStateAstroGoto_message.state}")
                                    my_logger.debug(f">> {getAstroStateName(ResNotifyStateAstroGoto_message.state)}")

                                if( WsPacket_message.type == 3):
                                    print("Decoding Response Notification Frame")
                                    ResNotifyStateAstroGoto_message = notify.ResNotifyStateAstroGoto()
                                    ResNotifyStateAstroGoto_message.ParseFromString(WsPacket_message.data)

                                    my_logger.debug(f"receive notification data >> {ResNotifyStateAstroGoto_message.state}")
                                    my_logger.debug(f">> {getErrorCodeValueName(ResNotifyStateAstroGoto_message.state)}")
                        else:
                            print("Ignoring Unkown Type Frames")
                    else:
                        print("No Messages Rcv : close ??")
                        self.wait_pong = False
                        self.stop_task.set()
                print("Continue .....")

        except websockets.ConnectionClosedOK  as e:
            print(f'Rcv: ConnectionClosedOK', e)
        except websockets.ConnectionClosedError as e:
            print(f'Rcv: ConnectionClosedError', e)
        except asyncio.CancelledError:
            print("Rcv Cancelled.")
        except Exception as e:
            # Handle other exceptions
            print(f"Rcv: Unhandled exception: {e}")
            if (not self.stop_task.is_set()):
                self.stop_task.set()
            await asyncio.sleep(1)
        finally:
            # Perform cleanup if needed
            print("TERMINATING Receive function.")

    async def send_message(self):
        # Create a protobuf message
        # Start Sending
        major_version = 1
        minor_version = 1
        device_id = 1  # DWARF II
        self.target_name = ""

        if not self.websocket:
            print("Error No WebSocket in send_message")
            return

        Send_TeleGetSystemWorkingState = True

        #CMD_CAMERA_TELE_GET_SYSTEM_WORKING_STATE
        WsPacket_messageTeleGetSystemWorkingState = base__pb2.WsPacket()
        ReqGetSystemWorkingState_message = camera.ReqGetSystemWorkingState()
        WsPacket_messageTeleGetSystemWorkingState.data = ReqGetSystemWorkingState_message.SerializeToString()

        WsPacket_messageTeleGetSystemWorkingState.major_version = major_version
        WsPacket_messageTeleGetSystemWorkingState.minor_version = minor_version
        WsPacket_messageTeleGetSystemWorkingState.device_id = device_id
        WsPacket_messageTeleGetSystemWorkingState.module_id = 1  # MODULE_TELEPHOTO
        WsPacket_messageTeleGetSystemWorkingState.cmd = 10039 #CMD_CAMERA_TELE_GET_SYSTEM_WORKING_STATE
        WsPacket_messageTeleGetSystemWorkingState.type = 0; #REQUEST
        WsPacket_messageTeleGetSystemWorkingState.client_id = self.client_id # "0000DAF2-0000-1000-8000-00805F9B34FB"  # ff03aa11-5994-4857-a872-b411e8a3a5e51

        # SEND COMMAND
        WsPacket_message = base__pb2.WsPacket()
        WsPacket_message.data = self.message.SerializeToString()

        WsPacket_message.major_version = major_version
        WsPacket_message.minor_version = minor_version
        WsPacket_message.device_id = device_id
        WsPacket_message.module_id = self.module_id
        WsPacket_message.cmd = self.command 
        WsPacket_message.type = self.type_id;
        WsPacket_message.client_id = self.client_id # "0000DAF2-0000-1000-8000-00805F9B34FB"  # ff03aa11-5994-4857-a872-b411e8a3a5e51
       
        try:
            # Serialize the message to bytes and send
            # Send Command
            await asyncio.sleep(0.02)

            if (Send_TeleGetSystemWorkingState):
                await self.websocket.send(WsPacket_messageTeleGetSystemWorkingState.SerializeToString())
                print("#----------------#")
                my_logger.debug(f"Send cmd >> {WsPacket_messageTeleGetSystemWorkingState.cmd}")
                my_logger.debug(f">> {getAstroCMDName(WsPacket_messageTeleGetSystemWorkingState.cmd)}")

                my_logger.debug(f"Send type >> {WsPacket_messageTeleGetSystemWorkingState.type}")
                my_logger.debug(f"msg data len is >> {len(WsPacket_messageTeleGetSystemWorkingState.data)}")
                print("Sendind End ....");  

            await asyncio.sleep(1)

            await self.websocket.send(WsPacket_message.SerializeToString())
            print("#----------------#")
            my_logger.debug(f"Send cmd >> {WsPacket_message.cmd}")
            my_logger.debug(f">> {getAstroCMDName(WsPacket_message.cmd)}")

            # Special GOTO  DSO or SOLAR save Target Name to verifiy is GOTO is success
            if ((self.command == protocol.CMD_ASTRO_START_GOTO_DSO) or (self.command == protocol.CMD_ASTRO_START_GOTO_SOLAR_SYSTEM)):
                self.target_name = self.message.target_name

            my_logger.debug(f"Send type >> {WsPacket_message.type}")
            my_logger.debug(f"Send message >> {self.message}")
            my_logger.debug(f"msg data len is >> {len(WsPacket_message.data)}")
            print("Sendind End ....");  

        except Exception as e:
            # Handle other exceptions
            print(f"Unhandled exception1: {e}")
        finally:
            # Perform cleanup if needed
            print("TERMINATING Sending function.")

    async def start(self):
        try:
            result = False  
            #asyncio.set_event_loop(asyncio.new_event_loop())
            #ping_timeout=self.ping_interval_task+2
            print(f"ping_interval : {self.ping_interval_task}")
            start_client = False
            self.stop_task.clear();
            async with websockets.connect(self.uri, ping_interval=None, extra_headers=[("Accept-Encoding", "gzip"), ("Sec-WebSocket-Extensions", "permessage-deflate")]) as websocket:
                try:
                    start_client = True
                    self.websocket = websocket
                    if self.websocket:
                        print(f"Connected to {self.uri} with {self.message}command:{self.command}")
                        print("------------------")

                    # Start the task to receive messages
                    #self.receive_task = asyncio.ensure_future(self.receive_messages())
                    self.receive_task = asyncio.create_task(self.receive_messages())

                    # Start the periodic task to send pings
                    #self.ping_task = asyncio.ensure_future(self.send_ping_periodically())
                    self.ping_task = asyncio.create_task(self.send_ping_periodically())

                    # Start the periodic task to abort all task after timeout
                    self.abort_tasks = asyncio.create_task(self.abort_tasks_timeout(90))

                    await asyncio.sleep(2)

                    # Send a unique message to the server
                    try:
                        await self.send_message()

                        # For python 11
                        #async with asyncio.TaskGroup() as tg:
                        #    self.receive_task = tg.create_task(self.receive_messages())
                        #    self.ping_task = tg.create_task(self.send_ping_periodically())

                        #print(f"Both tasks have completed now: {self.receive_task.result()}, {self.ping_task.result()}")
                        #await self.abort_tasks_timeout(30)

                        results = await asyncio.gather( 
                            self.receive_task,
                            self.ping_task,
                            self.abort_tasks,
                            return_exceptions=True
                        ) 
                        print(results)
                        print("End of Current Tasks.")

                        # get the exception #raised by a task

                        try:
                            self.receive_task.result()
                            self.ping_task.result()
                            self.abort_tasks.result()

                        except Exception as e:
                            print(f"Exception occurred in the Gather try block: {e}")

                        print("End of Current Tasks Results.")

                    except Exception as e:
                        print(f"Exception occurred in the try block: {e}")

                except Exception as e:
                    print(f"Exception occurred in the 2nd try block: {e}")
        except Exception as e:
            print(f"unknown exception with error: {e}")
        finally:
            # Signal the ping and receive functions to stop
            self.stop_task.set()

            # Cancel the ping task when the client is done
            if self.ping_task:
                print("Closing Ping Task ....")
                self.ping_task.cancel()
                try:
                    await self.ping_task
                except Exception as e:
                    print(f"unknown exception with error: {e}")

            # Cancel the receive task when the client is done
            if self.receive_task:
                print("Closing Receive Task ....")
                self.receive_task.cancel()
                try:
                    await self.receive_task
                except Exception as e:
                    print(f"unknown exception with error: {e}")

            # Close the WebSocket connection explicitly
            if start_client:
                if self.websocket: #and self.websocket.open:
                    print("Closing Socket ....")
                    try:
                        await self.websocket.close()
                        print("WebSocket connection closed.")
                    except websockets.ConnectionClosedOK  as e:
                        print(f'Close: ConnectionClosedOK', e)
                    except websockets.ConnectionClosedError as e:
                        print(f'Close: ConnectionClosedError', e)
                    except Exception as e:
                        print(f"unknown exception with error: {e}")

                print("WebSocket Terminated.")

# Run the client
def start_socket(message, command, type_id, module_id, uri=config.DWARF_IP, client_id=config.CLIENT_ID, ping_interval_task=10):
    websocket_uri = ws_uri(uri)

    print(f"Try Connect to {websocket_uri} for {client_id} with data:")
    print(f"{message}")
    print(f"command:{command}")
    my_logger.debug(f">> {getAstroCMDName(command)}")
    print("------------------")

    try:
        # Create an instance of WebSocketClient
        client_instance = WebSocketClient(websocket_uri, client_id, message, command, type_id, module_id, ping_interval_task)

        # Call the start method to initiate the WebSocket connection and tasks
        asyncio.run(client_instance.start())
        print("WebSocket Client End.")
        return client_instance.result;

    except Exception as e:
        # Handle any errors that may occur during the close operation
        print(f"Unknown Error closing : {e}")
        pass  # Ignore this exception, it's expected during clean-up

    return False;

def connect_socket(message, command, type_id, module_id):

    result = False

    try:
        # Call the start function
        result = start_socket(message, command, type_id, module_id)
        print(f"Result : {result}")

    except KeyboardInterrupt:
        # Handle KeyboardInterrupt separately
        print("KeyboardInterrupt received. Stopping gracefully.")
        pass  # Ignore this exception, it's expected during clean-up
    return result

