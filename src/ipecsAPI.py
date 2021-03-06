# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

# Imports
import  os, sys, time, stat
tmp = os.path.join(os.getcwd(), 'lib')
paths = sys.path
try:
    paths.index (tmp)
except ValueError as ex:
    sys.path.append(tmp)

import json
import ssl
import socket, websockets, requests, urllib3
import asyncio, subprocess
import logging
import threading
import time

from __version      import __version__, __product__
from websockets     import exceptions as ws_exceptions
from datetime       import datetime
from datetime       import timedelta
from threading      import Timer, Thread
from requests.auth  import HTTPBasicAuth
from ipecs_mongo    import ipecs_db_io

try:
    from ipecs_config  import ipecs_config
except json.JSONDecodeError as ex:
    raise (ex)

# iPECs API GLOBAL DEFINITIONS
LOGGING_ID              = 'iPECsAPI'

QUEUE_BUSY              = 1
QUEUE_IDLE              = 2
QUEUE_INCOMING_CALL     = 3
AGENT_ACD_LOGIN         = 11
AGENT_ACD_LOGOUT        = 12
AGENT_ACD_UNAVAIL       = 13
AGENT_ACD_AVAIL         = 14
AGENT_ACD_WUP_START     = 15
AGENT_ACD_WUP_END       = 16
STATION_BUSY            = 17
STATION_IDLE            = 18
STATION_DND_ACTIVE      = 19
STATION_DND_INACTIVE    = 20
STATION_SEIZED          = 41
STATION_CONNECTED       = 42
STATION_ABANDONED       = 43
STATION_DISCONNECTED    = 44
STATION_ON_HOLD         = 49
STATION_OFF_HOLD        = 50
STATION_ANSWERED        = 57
ACD_ON_HOLD             = 62
STATION_RINGING         = 66
OUTBOUND_CALL           = 67
SMDR_TIME_STAMP         = 68
SMDR_CALL_SUMMARY       = 69
DID_INFO_INCOMING       = 71
CALLER_INF_INCOMING     = 72
AGENT_HOTDESK_LOGIN     = 81
AGENT_OUT_OF_SERVICE    = 82
AGENT_HOT_DESK_LOGOUT   = 83
AGENT_IN_SERVICE        = 84
SMDR_INCOMING           = 88
SMDR_ICM                = 89
SMDR_CALL_TYPE          = 90
DELAY_ONLY              = 999

DIR_INBOUND             = True
DIR_OUTBOUND            = False

CALL_IS_UNDEFINED       = 0
CALL_IS_ACTIVE          = 1
CALL_IS_ONHOLD          = 2
CALL_IS_IN_QUEUE        = 3
CALL_IS_IN_WRAP         = 4
CALL_IS_CLOSED          = 5
CALL_IS_TRANSFERRED     = 6
CALL_IS_RINGING         = 7
CALL_IS_ABANDONED       = 8
CALL_DISCONNECTED       = 9

# Global Variables
queues_allowed:     list
phones_allowed:     list
events_allowed:     list
events_blocked:     list
station_list:       dict
resources:          dict     
stop_asyncio:       bool = False
wsock_connected:    bool = False
watchdog_active:    bool = False
ignore_events:      bool = False
missed_events:      int  = 0
ping_count:         int  = 0
last_err_msg:       str  = ''
system_up_timer:    datetime
wsock_loop:         asyncio
wsock_thread:       threading.Thread = None
# CHANGED wsock_loop          = asyncio.new_event_loop ()

class ipecsAPI ():
# Class definitions
    _notInitErr =       "iPECsAPI ->> class ipecsAPI has not been initialised properly!"
    _config:            ipecs_config
    _mongo:             ipecs_db_io
    _ssl_context:       ssl.SSLContext
    _http:              urllib3.PoolManager
    _log:               logging.Logger
    _period_start_time: datetime
    _stations:          object
    _ipecs:             dict
    _cmds:              dict
    _rsps:              dict
    _cmd_ary:           list
    _f_name:            str
    _f_log:             str  
    _baseURIExt:        str  
    _fullURI:           str
    _fullWSS:           str
    _srvIP:             str
    _sessiontoken:      str = ''
    _connectionTimer:   int
    _keep_alive_to:     int
    _port:              int
    _max_socket_retries:int
    _isLoggedIn:        bool = False
    _isInitialised:     bool = False
    _hasServerIP:       bool = False
    _has_error:         bool = False
    _timer_first_run:   bool = True
    _force_logout:      bool = True
    _login_in_progress: bool = False
    _simulation_active: bool = False
    _reset_timer:       object
    _main_event_loop:   object
    _ary_hooks:         list
    watchdog_timer:     Timer
# Callback related definitions
    _callback_func:         object
    _status_cb_func:        object
    _system_reset_func:     object
# Initialise
    """
    Function __init__ initialises ipecsAPI class.
    
    Parameters
    ----------
    f_name : the fqdn of the iPECsAPI configuration file, default is ipecs.conf
    log_id : the name that will precede log entries in the log file and console log.

    The function will raise an exception if anything goes wrong.
    """
    def __init__ (self, f_name:str = './ipecs.conf', log_id:str = 'iPECsAPI', simulation_active:bool = False, log_callback_func:object = None) -> None:
        self.__f_name = f_name
        try:
            global watchdog_active
            global queues_allowed
            global phones_allowed
            global events_allowed
            global events_blocked
            global system_up_timer

            # Set time stamps and initialise from parameters received
            system_up_timer         = datetime.now ()
            self._period_start_time = datetime.now ()
            self._status_cb_func    = log_callback_func
            self._simulation_active = simulation_active
            init_start_time         = time.perf_counter ()

            # Load the configuration File
            self.loadConfiguration (f_name, log_id)

        # TODO: Temporary global assignment of resources dictionary
            global resources
            resources = self._config.getResources ()

        # Make sure to avoid SSl errors
            #if self._config.ipecs_disable_SSL_warnings:
            if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
                self._log.info (self._config.getResourceString('inf', 'inf003'))
                ssl._create_default_https_context = ssl._create_unverified_context
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            #else:
                #urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ce_certs=certifi.where())
            self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE
            
        # Check if we have a valid iPECS uid and password stored in the config file
            if self._config.ipecs_pw_len > 0 and self._config.ipecs_uid_len > 0:
                self._config.encryptLoginDetails ('ipecs')
            else:
                raise ValueError (self._config.getResourceString('cipher', 'enc004').format(os.path.join(os.getcwd(), 'res', 'ipecs.conf')))
        # Only do the follwing code segment once the Mongo DB has been secured
        # this is signalled in ipecs.conf.mongo.db-secured [True/False]
            if self._config.mongo_db_secured:
                # Check if we have a valid mongo uid and pw stored in the config file
                if self._config.mongo_pw_len > 0 and self._config.mongo_uid_len > 0:
                    # Encrypt password and user ID
                    self._config.encryptLoginDetails ('mongo')
                else:
                    raise ValueError (self._config.getResourceString('cipher', 'enc005').format(os.path.join(os.getcwd(), 'res', 'ipecs.conf')))
            # Create Mongo management object - this includes creating database and collection
            # as well as starting a MongoDB connection monitor thread
            self._mongo = ipecs_db_io (res=self._config.getResources ('mongo'), conf=self._config.getSection ('mongo'), verbose=self._config.log_verbose)
            # Create Stations object
            self._stations = ipecsAPI.ipecsStations(
                            config=self._config.getSection ('ipecs'), 
                            call_summary=self._config.getDictCallSummary(), 
                            station_status=self._config.getDictStationStatus(), 
                            time_format=self._config._event_time_format, 
                            db=self._mongo, 
                            agent_summary=self._config.getDictAgentSummary(), 
                            missed_call_dict=self._config.getMissedCallDict (),
                            acd_summary=self._config.getDictACDSummary (), 
                            acd_history=self._config.getDictACDHistory (),
                            verbose=self._config.log_verbose)
            self._stations.addCallRingingHook (self.emit_call_notification)
            phones_allowed = self._config.ipecs_stations
            queues_allowed = self._config.ipecs_queues
        # This function needs to be called after _mongo is initialised
        # Create a Timer that will reset all counters to 0 at a time defined in the configuration file
            try:
                self._init_Reset_Timer ()
                # Only activate watchdog timer if we are in standard mode, NOT simulating the iPECs server
                if not self._simulation_active:
                    self._init_Watch_Dog_Timer ()
                else:
                    self._log.info (self._config.getResourceString('http', 'wss026'))
                # end if
            # There is a serious problem need to restart the whole system
            except ipecsAPI.exceptions.NotConnected:
                self._log.critical (self._config.getResourceString('err', 'err012'))
                self._system_reset_func ()
    # Initialisation complete - we can use his class now 
            init_end_time = time.perf_counter ()
            self._log.debug (self._config.getResourceString('msg', 'msg003').format(self.__class__, init_end_time - init_start_time))
            self._isInitialised = True
        except ValueError as ex:
            logging.fatal (ex)
            raise Exception (ex)
        except Exception as ex:
            logging.fatal (ex, exc_info=False)
            raise Exception (ex)

# Init watchdog timer
    def _init_Watch_Dog_Timer (self) -> None:
        self._watchdog_timer = Timer (self._config.socket_ping_interval, self._socket_watchdog_check)
        self._watchdog_timer.start()
        watchdog_active = True
# Delete
    """
    Function __del__ deletes ipecsAPI class.
    
    Parameters
    ----------
        None
    """
    def __del__ (self):
        try:
            if isinstance (self._fullWSS, str):
                del self._fullWSS
        except:
            pass
        try:
            if isinstance (self._baseWSS, str):
                del self._baseWSS
        except:
            pass
        try:
            if isinstance (self._srvIP, str):
                del self._srvIP
        except:
            pass
        try:
            if isinstance (self._fullURI, str):
                del self._fullURI
        except:
            pass
        try:
            if isinstance (self._baseURIExt, str):
                del self._baseURIExt
        except:
            pass
        try:
            if isinstance (self._cmd_ary, list):
                del self._cmd_ary
        except:
            pass
        try:
            if isinstance (self._cmds, dict):
                del self._cmds
        except:
            pass
        try:
            if isinstance (self._stations, ipecsAPI.ipecsStations):
                del self._stations
        except:
            pass
        # Since _config has already been shutdown, we don't need to delete the object
        try:
            if isinstance (self._log, logging.Logger):
                del self._log
        except:
            pass
# Shutdown
    """
    Function shutdown invokes objects shutdown function and then initiates self delete.
    
    Parameters
    ----------
        None
    """
    def shutdown (self, restart=False)-> None:
        # CHANGED global wsock_loop
        global wsock_thread
        global stop_asyncio
        # Stop socket event loop
        if wsock_thread.is_alive():
            stop_asyncio = True
            wsock_thread.join()
        # CHANGED if wsock_loop.is_running():
        # CHANGED     wsock_loop.call_soon_threadsafe(wsock_loop.stop)
        self._log.info (self._config.getResourceString ('inf', 'inf013').format (__product__))
        self._log.info (self.get_system_run_time ())
        if isinstance (self._stations, ipecsAPI.ipecsStations):
            self._stations.shutdown ()
        if isinstance (self._mongo, ipecs_db_io):
            self._mongo.shutdown()
        if isinstance (self._config, ipecs_config):
            if self._isLoggedIn:
                self._log.info (self._config.getResourceString ('http', 'http012').format (self._baseURIExt))
                #TODO uncomment self.logout ()
            # shutdown the config object -> this will make sure that any changes will get saved before deleting the object 
            self._config.shutdown ()
        return
# ==================== Definition of Class Properties ====================
    @property
    def Logger (self) -> logging.Logger:
        return self._config.Logger
    @property
    def op_codes (self) -> dict:
        return self._config.ipecs_op_codes
    @property
    def iPECsServerIP (self) -> str:
        return self._config.ipecs_server_ip
    @property
    def iPECsBaseWSS (self) -> str:
        return self._config.ipecs_wss_base
    @property
    def ipecsMongo (self) -> object:
        return self._mongo
    @property
    def ipecsConfig (self) -> object:
        return self._config
    @property
    def ipecsSimulationOFF (self) -> None:
        """ipecsSimulationOFF switches the simulation mode of iPECs Wrapper OFF.
        If Simulation mode is already off, no action is performed.
        """
        if self._simulation_active:
            self._simulation_active = False
            self._log.info (self._config.getResourceString('http', 'wss028'))
            self._init_Watch_Dog_Timer ()
            self.connectAPI ()
        else:
            # Signal no action taken as mode is already off
            self._log.info (self._config.getResourceString('http', 'wss029'))
            return
# ==================== Definition of Class Methods =======================
    def ResetCounters (self) -> dict:
        return self._resetCounters ()
    def getCurrentStats (self) -> dict:
        try:
            return {
                "System Runtime":   self.get_system_run_time (True), 
                "Period Start":     self._period_start_time, 
                "Period End":       datetime.now(), 
                "Call Stats":       self._stations.getCallStats(),
                "Agent Stats":      self._stations.getAgentStats ()
            }
        except Exception as ex:
            self._log.error (f'{self.__class__}getCurrentStats -> {ex}.')
        # Get system runtime
    def get_system_run_time (self, short=False) -> str:
        delta = datetime.now() - system_up_timer
        days, sec = delta.days, delta.seconds
        hrs = (days * 24 + sec // 3600) % 24
        mins = (sec % 3600) // 60
        sec = sec % 60
        if short:
            return f'{days} days, {hrs} hours, {mins} minutes, and {sec} seconds.'
        else:
            return self._config.getResourceString ('inf', 'inf014').format (__product__, days, hrs, mins, sec)
    # Load configuration
    def loadConfiguration (self, f_name: str, log_id: str) -> None:
        global events_allowed
        global events_blocked
        # Create configuration object - that will hold all configuration information
        # This needs to be the first point of call - if not, all subsequent calls will fail
        self._config                = ipecs_config (config_file_name=f_name, log_id=log_id, log_callback_function=self._status_cb_func)
        self._log                   = self._config.Logger
        self._cmds                  = self._config.getiPECsCommands ()
        self._cmd_ary               = self._config.getiPECsCommandArray ()
        self._baseURIExt            = self._config.getBaseURIExt ()
        self._baseURI               = self._config.ipecs_uri_base
        self._port                  = self._config.ipecs_port
        self._fullURI               = self._config.getFullURI ()
        self._baseWSS               = self._config.ipecs_wss_base
        self._srvIP                 = self._config.getiPECsServerIP ()
        self._fullWSS               = self._config.ipecs_wss_full.format (self._srvIP, self._config.ipecs_port, self._config.ipecs_uid)
        self._timeout               = self._config.ipecs_timeout
        self._retry_attempts        = self._config.ipecs_retry_attempts
        self._retry_rate            = self._config.ipecs_retry_rate
        self._keep_alive_to         = self._config.ipecs_keep_alive_timeout
        self._max_socket_retries    = self._config.ipecs_max_socket_retries
        events_allowed              = self._config.ipecs_supported_events
        events_blocked              = self._config.ipecs_blocked_events
    # Return configuration    
    def getConfiguration (self, section=None) -> dict:
        return self._config.getSection (section)
    # Get all resources from language file
    def getResources (self, section=None) -> dict:
        return self._config.getResources (section)
    # Get a single resource string
    def getResourceString (self, section, key) -> str:
        return self._config.getResourceString (section, key)
    # get ACD status
    def getACDStatus (self, all_data=True) -> dict:
        return self._stations.getACDSummary (all_data)
    # Call counter reset function
    def _resetCounters (self) -> None:
        try:
            msg = self._config.getResourceString ('inf', 'inf007')
            self._log.info (msg)
            # Save period summary data to database
            tss = datetime.now().strftime (self._config.mongo_date_format)
            call_summary   = self._stations.getCallStats ()
            agent_summary  = self._stations.getAgentStats ()
            period_summary = {"_id": tss, "Period Start": self._period_start_time, "Period End": datetime.now(), "Call Stats": call_summary, "Agent Stats:": agent_summary}
            self._mongo.updateEODSummary (pay_load=period_summary)
            if self._config.ipecs_metrics_reset_enabled:
                self._stations.reset_all ()
                self._period_start_time = datetime.now ()
        except Exception as ex:
            self._log.error (f'{self.__class__}_resetCounters -> {ex}.')
            pass
        finally:
            # restart timer
            self._init_Reset_Timer ()
    # Set Push of caller info for a extension
    def getConnectionStatus (self) -> dict:
        global wsock_connected
        s1 = 'not connected to iPECs server!'
        s2 = 'not connected to Mongo datebase server!'
        if wsock_connected:
            s1 = f'connected to iPECs server at [{self._baseURI}];'
        if self._mongo.mongo_connected:
            s2 = f'connected to Mongo database server at [{self._config.mongo_url}].'
        s3 = self.get_system_run_time ()
        return (f'{s3};\n{__product__} is {s1}\n{__product__} is {s2}')
    # Reset counters function for test purposes
    def tests_reset_counters (self) -> None:
        self._resetCounters ()
    # Set ignore_events flag
    def setIgnoreEventsFlag (self) -> str:
        global ignore_events
        ignore_events = True
        return self._config.getResourceString ('ipecs', 'msg003')
    # Clear ignore_events flag
    def clearIgnoreEventsFlag (self) -> str:
        global ignore_events
        ignore_events = False
        return self._config.getResourceString ('ipecs', 'msg004')
    # Get a list of connected Stations
    def getStationList (self) -> list:
        return self._stations.getStationList
# Test procedures
    def copydata (self) -> None:
        self._mongo.copySimulationData ()
# Read n lines from log-file
    def readLinesFromLogFile (self, num_lines:int = 5, log_level=None) -> list:
        """Read N file lines since last access until EOF is reached and return.
        """
        fname = self._config.log_file_name
        """Read last N lines from file fname."""
        if num_lines <= 0:
            return ('Invalid num_lines value %r' % num_lines)
        with open(fname, 'rb') as f:
            BUFSIZ = 1024
            # True if open() was overridden and file was opened in text
            # mode. In that case readlines() will return unicode strings
            # instead of bytes.
            encoded = getattr(f, 'encoding', False)
            CR = '\n' if encoded else b'\n'
            data = '' if encoded else b''
            f.seek(0, os.SEEK_END)
            fsize = f.tell()
            block = -1
            exit = False
            while not exit:
                step = (block * BUFSIZ)
                if abs(step) >= fsize:
                    f.seek(0)
                    newdata = f.read(BUFSIZ - (abs(step) - fsize))
                    exit = True
                else:
                    f.seek(step, os.SEEK_END)
                    newdata = f.read(BUFSIZ)
                data = newdata + data
                if data.count(CR) >= num_lines:
                    break
                else:
                    block -= 1
            lines = data.splitlines()[-num_lines:]
            text: str
            log_dict: dict = {}
            i = 1
            for line in lines:
                text = line.decode("utf-8")
                try:
                    text.index (LOGGING_ID)
                    log_dict.update ([(i, text)])
                    i += 1
                except:
                    continue
            return log_dict
# Simulate Events from iPECs
    def simulate_events (self, sim_parameters:dict) -> str:
        if sim_parameters is None:
            raise resources['err']['err011'].format (self.__class__)
        else:
            events:     dict  = {}
            i_event:    dict = {"data": {}}
            delay:      int = 3
            rec_cnt:    int = 0
            cur_cnt:    int = 1
            tmp_thread: threading.Thread

            events, rec_cnt = self._mongo.getSimulationRecords (sim_parameters['sim_rec_cnt'])
            for event in events:
                del event['_id']
                # Check which event we are dealing with and decide the delay between current and next event trigger
                code = event['eventCode']
                if code != OUTBOUND_CALL and code != STATION_RINGING and code != STATION_ANSWERED and code != QUEUE_INCOMING_CALL:
                    delay = sim_parameters['sim_exec_dly']
                if code == STATION_CONNECTED or code == STATION_SEIZED:
                    # call answered delay for defined time
                    delay = sim_parameters['sim_exec_dly']
                    # increment call length for next call
                    sim_parameters['sim_exec_dly'] += sim_parameters['sim_call_len_inc']
                dt_now = datetime.now()
                event['time']   = dt_now.strftime (self._config.ipecs_event_date_format)
                i_event['data'] = event
                tmp_thread = ipecsAPI.iPECsEventParserThread ('iPECs', 'SimEventsSub', i_event, self._config, self._mongo, self._stations)
                tmp_thread.setDaemon
                self._log.debug (f'Simulation processing record {cur_cnt} of {rec_cnt} total records.')
                cur_cnt += 1
                tmp_thread.start ()
                time.sleep (delay)
                tmp_thread.join()
            # End for loop
            return resources['inf']['inf015']
# Simulate iPECs Command
    def simulate_ipecs_command (self, cmd: dict) -> None:
        try:
            sim_thread = ipecsAPI.iPECsEventParserThread ('iPECs', 'SimCommand', cmd, self._config, self._mongo, self._stations, sim=True)
            sim_thread.setDaemon
            sim_thread.start ()
            sim_thread.join ()
        except Exception as ex:
            self._log.error (self._config.getResourceString('sim', 'sim003').format(self.__class__, 'simulate_ipecs_command', ex))
# Initialise and start reset timer
    def _init_Reset_Timer (self) -> None:
        reset_time = time.strptime (self._config.ipecs_metrics_reset_time, '%H:%M:%S')
        # If this is the first run, do not add a new day to the reset timer, first reset will occur same day as API is run
        x = datetime.now()
        if self._timer_first_run:
            # If config requires 24 hour reset time, just add another day and set to 00:00:00
            if self._config.ipecs_metrics_reset_time == '00:00:00' or self._config.ipecs_metrics_reset_time == '23:59:59':
                y = x.replace (day=x.day, hour=23, minute=59, second=59, microsecond=0)
            else:
                y = x.replace (day=x.day, hour=reset_time.tm_hour, minute=reset_time.tm_min, second=reset_time.tm_sec, microsecond=0)
            self._timer_first_run = False
        else:
            # If config requires 24 hour reset time, just add another day and set to 00:00:00
            if self._config.ipecs_metrics_reset_time == '00:00:00' or self._config.ipecs_metrics_reset_time == '23:59:59':
                y = x.replace (day=x.day, hour=23, minute=59, second=59, microsecond=0) + timedelta (days=1)
            else:
                y = x.replace (day=x.day, hour=reset_time.tm_hour, minute=reset_time.tm_min, second=reset_time.tm_sec, microsecond=0) + timedelta (days=1)
        delta_t = y - x
        try:
            self._log.info (self._config.getResourceString ('inf', 'inf008').format (y.strftime ('%Y-%m-%d'), y.strftime ('%H:%M:%S')))
            reset_timer = Timer (delta_t.total_seconds (), self._resetCounters)
            reset_timer.start()
        except Exception as ex:
            self._log.error (resources['err']['errgen'].format(self.__class__, '_init_Reset_Timer', ex))
# System Login function combined login into http and socket
    """
    The rational for the following code is based on the fact that at times the iPECs server disconnects the socket 
    connection(reason unknown atm). If a that happens, the iPECsAPI wrapper will raise two possible exceptions: 
    - ConnectionClosed, or 
    - NotConnected
    These exceptions need to be caught and the wrapper needs to re-connect to the iPECs API.
    When the iPECs server disconnects the socket, it is probable that the logged in user has also been logged out, 
    which in turn means that the session token received during login is invalid and a new session token needs 
    to be created via a renewed login. Hence, the whole process needs to be repeated

        Raises:
        ipecsAPI.exceptions.ConnectionClosed: raised when the server dropped the connection
        ipecsAPI.exceptions.NotConnected:  raised when a connection cannot be established

    """
    def connectAPI (self):
        global last_err_msg
        global stop_asyncio
        global wsock_thread
        # CHANGED global wsock_loop
        # Only execute the connect if not in simulation mode
        if self._simulation_active:
            self._log.info (self._config.getResourceString('http', 'wss025'))
            return
        # end if sim active
        # set connection error to True, so that the while loop executes
        stop_asyncio  = False
        con_err: bool = True
        attempts: int = 0

        # First try to log out
        if self.UserLoggedIn:
            try:
                self.sendCommand ('logout')
            except Exception as ex:
                self._log.warning (self._config.getResourceString ('err', 'errgen').format(self.__class__, 'connectAPI', ex))
        while con_err and attempts < self._max_socket_retries:
            try:
                attempts += 1
                self._login_in_progress = True
                # Log into the iPECs API - user info is derived from configuration file
                # Login command will raise an error if login attempts exceed defined number of retries
                try:
                    self.sendCommand ('login')
                except self.exceptions.LoginRetryAttemptsExceeded as ex:
                    con_err = True
                    raise ex
                # all clear, reset everything so that if connection gets lost it can restart
                con_err  = False
                attempts = 0
                if wsock_thread is not None and wsock_thread.is_alive():
                    # Check if wsock_loop is running and stop it it is -> This is done by signalling stop_asyncio = True
                    # This needs to be done before joining the thread, as the asyncio loop is started within the thread
                    stop_asyncio = True
                    # Stop the wsock_thread 
                    wsock_thread.join()
                # Initiate Secure WEB Socket - this part can only run after successfull login
                # This will also restart the thread and asyncio loop
                self.startSocketListener ()
                con_err = False
                self._login_in_progress = False
                if attempts >= self._max_socket_retries:
                    last_err_msg = self._config.getResourceString('http', 'wss020').format (attempts)
                    raise self.exceptions.NotConnected (last_err_msg)
            # Danger - while loop -> will run forever
                while not con_err:
                    time.sleep (0.01)
            except self.exceptions.ServerUnreachable as ex:
                raise self.exceptions.ServerUnreachable (ex)
            except self.exceptions.ConnectionClosed:
                con_err = True
                time.sleep (5)
                continue
            except self.exceptions.NotConnected:
                con_err = True
                time.sleep (5)
                continue
            # Handle unknown or generic error by raising an exception
            except Exception as ex:
                con_err = True
                raise (ex)
#            if con_err and attempts >= self._max_socket_retries:
#                last_err_msg = self._config.getResourceString('http', 'wss020').format (attempts)
#                raise self.exceptions.NotConnected (last_err_msg)
# Check if user is checked in
    """
    Function isUserLoggedIn checks whether a user is already logged into the iPECs API.
    
    Parameters
    ----------
    none : nil.

    Returns:
    ----------
    Boolean:    True - if user is already logged in,
                False - if user is not logged in
    """
    @property
    def UserLoggedIn (self) -> bool:
        return self._isLoggedIn
# Check HTTP Error Response - Helper function to check HTTP response for errors
    """
    Function _httpCheckResponse checks the HTTP response received from a http request sent.
    It will log the error details in the _log and then throw an exception of type <requests.exceptions.HTTPError>
    if there are errors. It will return with None if all is clear.
    
    Parameters
    ----------
    none : nil.

    Returns:
    ----------
    None:    
    """
    def _httpCheckResponse (self, response, command, uri):
        err:  str
        json = response.json()
        # Server error
        if response.status_code >= 500:
            err = self._config.getResourceString('http','500').format(response.status_code, json['error']['message'], uri)
            self._log.error(err)
            raise requests.exceptions.HTTPError (err)
        # URL not found
        elif response.status_code == 404:
            err = self._config.getResourceString('http','404').format(response.status_code, json['error']['message'], command)
            self._log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # Operation forbidden
        elif response.status_code == 403:
            err = self._config.getResourceString('http', '403').format(response.status_code, json['error']['message'], uri)
            self._log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # Authentication Failed or Access not authorised
        elif response.status_code == 401:
            err = self._config.getResourceString('http', '401').format(uri, response.status_code, json['error']['message'])
            self._log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # Bad Request
        elif response.status_code == 400:
            err = self._config.getResourceString('http', '400').format(response.status_code, json['error']['message'], uri)
            self._log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # Unexpected Redirect
        elif response.status_code >= 300:
            err = self._config.getResourceString('http', '300').format(response.status_code, json['error']['message'], uri)
            self._log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # All good to go
        elif response.status_code == 200:
            self._log.info (self._config.getResourceString('http', '200').format(command))
            return
        else:
            # Unexpected Error
            err = self._config.getResourceString('http', '100').format(uri, response.status_code, json['error']['message'])
            self._log.error (err)
            raise requests.exceptions.HTTPError (err) 
# Send a Command to iPECs SMDR Interface  - Function filters, prepares parameters and sends command to be send to iPECs API to appropriate command function
    """
    Function sendCommand() -> dictfilters, prepares parameters and sends command to be send to iPECs API to appropriate command function.
    If there is an error the function will raise an Exception - you need to check log file to see error details.
    
    Parameters
    ----------
    command :   <str> [required] the code of the main command to be used. Valid command codes can be found in ipecs_commands.json
    opcode :    <str> [optional] the sub-code (parameter string) of the main command to be used. Valid command op-codes can be found in ipecs_commands.json
    user :      <str> [optional] the user account to be used for this command - the user should be the same user as has been logged in before.
    pw :        <str> [optional] the password for the user account to be used for this command - only required when logging user in for the first time.
    arg1-arg4 : <str> [optional] optional parameters required by command to be executed.

    Returns:
    ----------
    dict:   <json> json dictionary if command returns data otherwise None.
    """

    def sendCommand (self, command, opcode=None, arg1=None, arg2=None, arg3=None, arg4=None) -> json:
        # The class is not properly initialised, cannot function - raise exception
        if not self._isInitialised:
            raise RuntimeError (self._config.getResourceString('ipecs', 'err002').format(command, self._config.command_file, "commands"))
        if not self._isLoggedIn and command != 'login':
            raise UserWarning (self._config.getResourceString('http', 'http003'))
        
        # Check if the desired command is listed in the supported commands list
        try:
            self._cmd_ary.index(command)
        except ValueError:
            self._log.error (self._config.getResourceString('ipecs', 'err002').format(command, self._config.command_file, "commands"))
            raise NotImplementedError (self._config.getResourceString('ipecs', 'err003').format(command))
        try:
            self._log.debug (self._config.getResourceString('dbg', 'dbg003').format (command))
            if command == 'login': 
                self.login ()
                return None
            elif command == 'logout': 
                self.logout ()
                return None
            elif command == 'smdr':
                # TODO: this part still needs to be verified and changed according to needs
                params = {}
                if arg1 is not None:
                    for key, value in arg1.items():
                        params[key] = value
                if arg2 is not None:
                    for key, value in arg2.items():
                        params[key] = value
                if arg3 is not None:
                    for key, value in arg3.items():
                        params[key] = value
                if arg4 is not None:
                    for key, value in arg4.items():
                        params[key] = value
                return self._smdr (params)
            else:
                raise NotImplementedError (self._config.getResourceString('ipecs', 'wrn001').format(command))
        except Exception as ex:
            raise ex
# Login user to iPECs HTTP - Send login command to iPECs Server API
    """
    Function login() -> bool sends the login command to the iPECs API.
    If there is an error the function will raise an Exception - you need to check log file to see error details.
    
    Parameters
    ----------
    user :  the user account to be used for this command.
    pw:     the password for the user account to be logged in     

    Returns:
    ----------
    bool:   True if user has been successfully logged in,
            False if user has not been logged in.
    """
    def login (self):
        _password: str
        _user: str
        _cmd: str
        _header: dict
        _verify: bool
        _time_start = time.perf_counter()
        # Make sure this class is fully initialised
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        # Check if user is already logged in - if yes, do nothing and return
        if self._isLoggedIn:
            self._log.info (self._config.getResourceString('http', 'http001'))
            return
        try:
            _msg: str = ''
            # Get the command json and add the info missing
            _cmd = self._cmds['login'].format(self._fullURI, self._config.ipecs_uid)
            if self._log.level == logging.DEBUG:
                self._log.debug (self._config.getResourceString('dbg', 'dbg005').format(_cmd))
            # get login info, no need to load this for every retry attempt
            _retry_rate     = self._config.ipecs_retry_rate
            _retry_attempts = self._config.ipecs_retry_attempts
            _verify         = self._config.ipecs_verify
            _header         = self._config.getiPECsHeader('hdr_login')
            _password       = self._config.ipecs_password
            _user           = self._config.ipecs_uid
            
            self._log.info (self._config.getResourceString('http', 'http009'))
            for i in range (0, _retry_attempts, 1):
                try:
                    # Send the actual login command
                    response = requests.get(_cmd, auth=HTTPBasicAuth(_user, _password), headers=_header, verify=_verify)
                # Capture Socket timeout to retry
                except socket.timeout:
                    _msg = self._config.getResourceString('http', 'http008').format(response.status_code, _retry_rate)
                    self._log.debug(_msg)
                    time.sleep (_retry_rate)
                    continue
                # Check if the response is a 401 - means the user is already logged on or not authorised
                if response.status_code == 401:
                    if i == _retry_attempts - 1:
                        # We have reached the maximum number of retries, bail out
                        self._isLoggedIn = False
                        _msg = self._config.getResourceString('http', 'http006').format(self._baseURIExt, self._config.ipecs_port, _retry_attempts)
                        raise self.exceptions.LoginRetryAttemptsExceeded (_msg)
                    else:
                        json = response.json()
                        if json['error']['code'] == 2: # Invalid login information
                            raise ValueError (self._config.getResourceString('err', 'err007').format(self._baseURIExt))
                        else:
                            # It seems the same user is already logged in - try to send the logout command first - then retry
                            if self._force_logout:
                                self._log.warning(self._config.getResourceString('http', 'http102'))
                                # Try to load a previous session Token and logout with that. 
                                # This will only work if the connection was last within the last 90 seconds
                                self._sessiontoken = self._config.ipecsGetSessionToken ()
                                if self.logout ():
                                    time.sleep (_retry_rate)
                                # tried logout command, do not try again
                                self._force_logout = False
                            # Now lets try login command again
                            _msg = self._config.getResourceString('http', 'http007').format(response.status_code, _retry_rate, json['error']['message'], i+2)
                            self._log.warning (_msg)
                            time.sleep (_retry_rate)
                else:
                    # This is not a 401 response, so let's check what we have - the check will throw an exception if response is not 200 
                    self._httpCheckResponse (response, _cmd, self._baseURIExt)
                    # Get the response
                    resp = response.json()
                    # Get the token
                    self._sessiontoken = resp['token']
                    # Save session token for later
                    self._config.ipecsSaveSessionToken (resp['token'])
                    # get the timeout reported by the server
                    self._connectionTimer = resp['checkConnectionTimer']
                    _msg = self._config.getResourceString ('http', 'http010').format (self._baseURIExt, resp['checkConnectionTimer'], resp['systemType'], resp['systemVersion'], resp['apiVersion'])
                    self._log.info (_msg)
                    self._isLoggedIn = True
                    break
        except urllib3.exceptions.InsecureRequestWarning:
            msg = self._config.getResourceString('http', 'http004').format(self._baseURIExt)
            self._log.error (msg)
            raise Exception (msg)
        except Exception as ex:
            self._log.fatal (ex)
            raise Exception (ex)
        finally:
            _time_diff = time.perf_counter() - _time_start
            self._log.info (self._config.getResourceString ('inf', 'inf006').format ('login', _time_diff))
            if isinstance (_user, str):
                del _user
            if isinstance (_password, str):
                del _password
            if isinstance (_header, dict):
                del _header
            if isinstance (_cmd, str):
                del _cmd
# Notify CRM of inbound Call    
    def emit_call_notification (self, station_id: str, call_id: str, time_stamp: str) -> None:
        global queues_allowed
        global phones_allowed
        _header: dict
        _cmd:    str
        _verify: bool

        if  call_id is not None and station_id is not None:
            # Don't emit calls for queue
            if int (station_id) in queues_allowed or int (station_id) < phones_allowed[0] or int (station_id) > phones_allowed[1]:
                return
            _verify = self._config.ipecs_verify
            _cmd    = self._cmds['call-notify'].format(station_id, call_id, time_stamp)
            _header = self._config.getiPECsHeader('call_notification')
            self._log.debug (self._config.getResourceString('http', 'http013').format(call_id, station_id, _cmd))
            try:
                # Notify CRM of inbound call -> using a very short timeout as we don't want the reply
                requests.head (_cmd, headers=_header, timeout=0.00000001)
            except requests.exceptions.ReadTimeout: 
                pass
            except requests.exceptions.HTTPError as ex:
                self._log.error (ex)
            except requests.exceptions.RequestException as ex:
                self._log.error (ex)
            except Exception as ex:
                self._log.error (ex)
        else:
        # Error -> one or both of the parameters are None
            self._log.error (self._config.getResourceString('http', 'err002'))
# TODO: Make check connection asynchronous
# checkConnection - Send a Check Connection Request to keep connection alive
        """[Send a Check Connection Request to keep connection alive]
        """
    def checkConnection (self, user='admin'):
        try:
            cmd = self._cmds['checkconnection'].format(self._baseURIExt, user)
            self._log.debug (self._config.getResourceString('inf', 'inf002').format(cmd))
            try:
                hed = self._config.getiPECsHeader('hdr_logout')
                hed['Authorization'].value = hed['Authorization'].value.format (self._sessiontoken)
                response = requests.post(cmd, headers=hed, verify=self._config.ipecs_verify)
                self._httpCheckResponse (response, cmd, self._baseURIExt)
                self._isLoggedIn = True
            except requests.exceptions.HTTPError as ex:
                self._isLoggedIn = False
                raise Exception (ex)
            finally:
                del hed
        except Exception as ex:
            self._log.critical (ex)
        finally:
            del cmd

    #async def asyncCheckCon (self, cmd, headers, verify):
# Log User out of iPECs System - Send logout command to iPECs Server API
    """
    Function logout() -> bool sends the logout command to the iPECs API.
    If there is an error the function will raise an Exception - you need to check log file to see error details.
    
    Parameters
    ----------
    user :      the user account to be used for this command - the user should be the same user as has been logged in before.

    Returns:
    ----------
    bool:   True if user has been successfully logged out,
            False if user has not been logged out.
    """
    def logout (self) -> bool:
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        if not self._isLoggedIn and not self._force_logout or self._sessiontoken == "":
            self._log.debug (self._config.getResourceString('http', 'http002').format('logout'))
            return
        try:
            cmd = self._cmds['logout'].format(self._fullURI, self._config.ipecs_uid)
            self._log.debug (self._config.getResourceString('inf', 'inf002').format(cmd))
            try:
                hed = self._config.getiPECsHeader('hdr_logout')
                hed['Authorization'] = hed['Authorization'].format (self._sessiontoken)
                self._log.debug (f'{self.__class__}.logout() -> before post request -> command=[{cmd}] >>> header=[{hed}]')
                response = requests.post(cmd, headers=hed, verify=self._config.ipecs_verify)
                self._httpCheckResponse (response, cmd, self._baseURIExt)
                return True
            except urllib3.exceptions.InsecureRequestWarning as ex:
                self._log.error (ex)
                return False
            except requests.exceptions.SSLError as ex:
                self._log.error (ex)
                return False
            finally:
                del hed
        except KeyError as ex:
            self._log.error (self._config.getResourceString('err', 'err002').format (ex))
            return False
        except Exception as ex:
            self._log.error (ex)
            return False
        finally:
            self._isLoggedIn = False
            del cmd
# Send SMDR command  - Send SMDR command to iPECs Server API
    """
    Function __smdr sends a command including parameters to the iPECs API.
    If there is an error the function will raise an error - you need to check log file to see error details.
    The function will return a json object containing the data (if any) received from the iPECs server.
    If there is no data the function returns 'None'
    
    Parameters
    ----------
    user :      the user account to be used for this command - the user should be the same user as has been logged in before.
    params :    a json construct of the parameters required by the smdr command {"key1": "value1", "key2": "value2:, etc.}
                the params can also contain a complex json, such as {"key1: {"subkey": "value"}}

    Returns:
    ----------
    JSON object: The JSON object that was return by the server or None.
    """
    def _smdr (self, params=None) -> dict:
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        if not self._isLoggedIn:
            self._log.info (self._config.getResourceString('http', 'http002'))
            return
        try:
            cmd = self._cmds['smdr'].format(self._fullURI, self._config.ipecs_uid)
            self._log.debug (self._config.getResourceString('inf', 'inf002').format(cmd))
            try:
                hed = self._config.getiPECsHeader ('hdr_auth').format (self._sessiontoken)
                response = requests.get (cmd, headers=hed, params=params, verify=self._config.ipecs_verify)
                self._httpCheckResponse (response, cmd, self._baseURIExt)
                json = response.json()
                return json
            except urllib3.exceptions.InsecureRequestWarning as ex:
                self._log.error (ex)
            except requests.exceptions.SSLError as ex:
                self._log.error (ex)
        except KeyError as ex:
            self._log.error (self._config.getResourceString('err', 'err002').format (ex))
        except Exception as ex:
            self._log.fatal (ex)
# -------------------------------------------------------------------------------------------------
#   DEFINITION FOR IPECS_WEBSOCKET
# -------------------------------------------------------------------------------------------------
# Socket connection watchdog checker
    def _socket_watchdog_check (self):
        global wsock_connected
        global missed_events
        global watchdog_active
        global stop_asyncio
        global system_up_timer

        # Just to be sure --> if simulation is active return immediately
        # This should actually not be called in simulation mode
        # TODO: Remove the simulation check after debug
        if self._simulation_active:
            wsock_connected = True
            missed_events = 0
            return

        if self._watchdog_timer.finished:
            self._watchdog_timer.cancel()
            self._watchdog_timer = Timer (self._config.socket_ping_interval, self._socket_watchdog_check)
            self._watchdog_timer.start()
        if not wsock_connected and not self._login_in_progress and not stop_asyncio:
            if ping_count >= 2 or self._has_error:
                try:
                    missed_events += 1
                    err_msg = self._config.getResourceString ('http', 'wss018')
                    self._log.warning (err_msg)
                except:
                    pass
            if missed_events > self._config.ipecs_max_missed_pings:
                try:
                    stop_asyncio = True
                    time.sleep (5)
                    self._isLoggedIn = False
                    self.shutdown (restart=True)
                    self.connectAPI ()
                except (self.exceptions.NotConnected, self.exceptions.LoginRetryAttemptsExceeded, self.exceptions.ServerUnreachable) as ex:
                    raise ipecsAPI.exceptions.NotConnected (ex)
        else:
            missed_events = 0
            # Set wsock_connected to False - if we receive event 68 from api it will set connected to True
            wsock_connected = False
        return
# Socket connection thread wrapper
    def _startSocketAsyncio (self) -> None:
        global wsock_loop
        # we need to create a new loop for the thread, and set it as the 'default'
        # loop that will be returned by calls to asyncio.get_event_loop() from this thread.
        wsock_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(wsock_loop)
        wsock_loop.create_task(self._ipecsSocketListener())
        wsock_loop.run_forever()
# Need to await the 
# Start Socket Listener
    def startSocketListener (self):
        global wsock_loop
        global wsock_thread
        global wsock_connected
        global stop_asyncio
        # CHANGED if wsock_loop.is_running():
        # CHANGED     self._log.info (self._config.getResourceString ('http', 'wss023').format(self.__class__))
        # CHANGED     wsock_loop.call_soon_threadsafe(wsock_loop.stop)
        # CHANGED     self._log.info (self._config.getResourceString ('http', 'wss024').format(self.__class__))
        self._has_error = False

        if not self._simulation_active:
            self._log.info (self._config.getResourceString('http', 'wss027'))
            return
        # end if sim active

        # Only execute if not in simulation mode
        # Check if wsock_thread is running, if it is stop it
        if wsock_thread is not None:
            if wsock_thread.is_alive():
                try:
                    self._log.info (self._config.getResourceString ('http', 'wss023').format(self.__class__))
                    stop_asyncio = True
                    if wsock_loop is not None:
                        wsock_loop.close()
                    wsock_thread.join()
                    self._log.info (self._config.getResourceString ('http', 'wss024').format(self.__class__))
                except Exception as ex:
                    self._log.error (self._config.getResourceString('err', 'errgen').format(self.__class__, 'startSocketListener', ex))
                    self._has_error = True
        # Test if iPECs server is actually reachable
        if not self._config.is_iPECsPortOpen (self._srvIP, self._port):
            self._has_error = True
            raise self.exceptions.ServerUnreachable (self._config.getResourceString ('http', 'wss021').format (self._srvIP, self._port))
        else:
            self._log.info (self._config.getResourceString ('http', 'wss022').format(self._srvIP, self._port))
        # Start the socket listener and let it run forever - or until it crashes :-)
        try:
            self._log.debug (self._config.getResourceString('http', 'wss011'))
            # Start the thread that will start the async loop
            stop_asyncio = False
            wsock_thread = Thread (target=self._startSocketAsyncio, daemon=True)
            wsock_thread.start()
            self._log.info (self._config.getResourceString('http', 'wss008').format(self._srvIP))
            # CHANGED wsock_loop.create_task (self._ipecsSocketListener())
            # CHANGED wsock_thread = Thread (wsock_loop.run_forever())
        except self.exceptions.ConnectionRefused:
            # Connection was refused need to try to reconnect
            self.connectAPI ()
        except asyncio.exceptions.TimeoutError as ex:
            self._has_error = True
            self._log.error (self._config.getResourceString ('err', 'err008').format (ex))
            raise ipecsAPI.exceptions.ConnectionClosed (self._config.getResourceString('http', 'wss009').format(self._srvIP))
        except Exception as ex:
            self._has_error = True
            self._log.error (self._config.getResourceString ('err', 'err008').format (ex))
            raise ipecsAPI.exceptions.NotConnected (self._config.getResourceString('http', 'wss019').format(ex.args[0], self._srvIP))
        if self._has_error and not wsock_connected: 
            raise ipecsAPI.exceptions.ConnectionClosed (self._config.getResourceString('http', 'wss009').format(self._srvIP))
# Async Functions
    async def _ipecsSocketListener (self):
        """async_processing starts the asynchronous process to listen to the socket connection

        Raises:
            self.ConnectionRefused: raised when the server refuses the connection
            self.ConnectionClosed:  raised when the server closes the connection
        """
        _thread_id = 1
        global stop_asyncio
        global events_allowed
        global queues_allowed
        global phones_allowed
        global ping_count
        global wsock_connected
        global ignore_events
        global wsock_thread
        # global mongo_loop
        try:
            _has_con_err: bool
            # The code will only reach here is the socket is connected
            hed = self._config.getiPECsHeader ('hdr_wss')
            hed['Authorization'] = hed['Authorization'].format (self._sessiontoken)
            hed['Origin'] = hed['Origin'].format (self._baseURI, self._port)
            if self._log.level is logging.DEBUG:
                self._log.debug ("Socket Connection Parameters are: [{0}] - [{1}] ".format (self._fullWSS, hed))
            wsock_connected = True
            async with websockets.connect(
                self._fullWSS, 
                ssl=self._ssl_context, 
                ping_interval=self._config.ipecs_socket_timeout * 0.95, 
                ping_timeout=self._config.ipecs_ping_timeout,
                extra_headers=hed) as websocket:
                self._log.info = self._config.getResourceString ('http', 'wss008').format (self._srvIP)
                # Loop for result
                while not stop_asyncio:
                    err_msg = ''
                    _has_con_err = False
                    try:
                        # receive message
                        message = await websocket.recv()
                        event   = json.loads(message, strict=False)
                        code    = event['data']['eventCode']
                        data    = event['data']
                        try:
                            x = data['callRefID']
                            if x is not None:
                                pass
                        except:
                            data['callRefID'] = 'N/A'
                        try:
                            source = int (event['data']['sourceNumber'])
                        except:
                            source = 0
                        try:
                            target  = int (event['data']['destNumber'])
                        except:
                            target = 0
                        # Filter out any events that are not supported
                        if code in events_allowed:
                            # This is the iPECs timer event that comes every 60 seconds
                            if code == SMDR_TIME_STAMP:
                                if ping_count < 3:
                                    ping_count += 1
                                wsock_connected = True
                                continue
                            # Log event received
                            if self._config.log_verbose and self._log.level == logging.DEBUG and self._config.log_raw_events:
                                self._log.debug (self._config.getResourceString ('ipecs', 'msg002').format (data))
                            # TODO: remove this after debugging
                            # This flag is set through Flask app during runtime and if true will ignore (NOT PROCESS) the events received from iPECs
                            if ignore_events:
                                continue
                            # Filter out any phone extensions and queues that are not configured
                            if (source >= phones_allowed[0] and source <= phones_allowed[1]) or source in queues_allowed or (target >= phones_allowed[0] and target <= phones_allowed[1]) or target in queues_allowed:
                                if self._config.event_simulation:
                                    trd = Thread (target=self._mongo.logEvent, args=(data, self._config.event_simulation, ))
                                    trd.start()
                                self._thread = ipecsAPI.iPECsEventParserThread (_thread_id, 'iPECsEventParser', event, self._config, self._mongo, self._stations)
                                self._thread.setDaemon
                                self._thread.run ()
                                continue
                        else:
                            if self._config.log_verbose and self._log.level == logging.DEBUG:
                                self._log.debug (self._config.getResourceString ('http', 'wss017').format (code, __version__))
                    except json.JSONDecodeError as ex:
                        err_msg = self._config.getResourceString ('http', 'wss016').format (data, ex)
                    except ws_exceptions.ConnectionClosedOK as ex:
                        err_msg = self._config.getResourceString ('http', 'wss014a').format (self._srvIP)
                        _has_con_err = True
                    except ws_exceptions.ConnectionClosedError as ex:
                        err_msg = self._config.getResourceString ('http', 'wss014b').format (self._srvIP, ex)
                        _has_con_err = True
                    except ws_exceptions.ConnectionClosed as ex:
                        err_msg = self._config.getResourceString('http', 'wss014').format (self._srvIP, ex)
                        _has_con_err = True
                    finally:
                        if err_msg != '':
                            self._log.warning (err_msg)
                        if _has_con_err:
                            # Try recover socket connection
                            wsock_connected = False
                            if not stop_asyncio:
                                self.connectAPI ()
                try:
                    await websocket.close()
                except:
                    pass
                return
        except ws_exceptions.InvalidStatusCode as ex:
            self._has_error = True
            err = ''
            code = 0
            try:
                code = ex.status_code
            except:
                pass
            err = ex.args[0]
            if code == 400:
                self._log.error (self._config.getResourceString('http', 'wss013').format (err, self._srvIP))
                raise self.exceptions.ConnectionRefused (err, code)
            if code == 401:
                # This error is most likely due to a timeout between https authorization (login) and establishing of web socket
                self._log.error (self._config.getResourceString ('http', '401').format(self._srvIP, code, ex))
                raise ipecsAPI.exceptions.ConnectionRefused ()
        except Exception as ex:
            self._has_error = True
            raise self.exceptions.ConnectionClosed (ex)
# -------------------------------------------------------------------------------------------------
#   DEFINITION FOR CALLBACK FUNCTIONS
# -------------------------------------------------------------------------------------------------
    def addEventHook (self, function: object) -> None:
        if function is not None:
            self._stations.addEventHook (function)
    def addSystemResetEventHook (self, function: object):
        if function is not None:
            self._system_reset_func = function

    
    #def addStationBusyHook (self, function: object) -> None:
    #    self._stations.addStationBusyHook (function)
# -------------------------------------------------------------------------------------------------
#   MAIN EVENT PARSER & THREADING FUNCTION DEFINITION
# -------------------------------------------------------------------------------------------------
    def iPECsEventParser (self, ipecs_event: dict, config: ipecs_config, mongo: ipecs_db_io, stations: object, sim:bool=False) -> None:
        """iPECsEventParser analyses the Event data returned by the server through the socket connection.
        This code runs as a thread.

        Args:
            ipecs_event (dict): the ipecs_event data received from the server

        Raises:
            exception: 
            UnknownEventFormat - if flag to raise exception is set in config file
            Otherwise the function creates a log entry with the raw ipecs_event data
        """
        global events_allowed
        global events_blocked
        # check if the ipecs_event data is formated as a dictionary
        if isinstance (ipecs_event, dict) and ipecs_event is not None:
            global ping_count
            global wsock_connected
            # global mongo_loop
            _log = logging.getLogger (LOGGING_ID)
            _ipecs_event: dict = {}
            # Check that this ipecs_event data is in fact from the iPECs acd engine
            try:
                _delay: float = 0
                _ipecs_event = ipecs_event['data']
                if sim:
                    _delay = float (ipecs_event['delay'])
                event_code  = _ipecs_event['eventCode']
                station     = _ipecs_event['sourceNumber']
            # If troubleshooting is enabled, ALL Events will be logged
                if config.enable_troubleshooting:
                    event_string = _ipecs_event['eventString']
                    target:str = str (_ipecs_event['destNumber'])
                    if target.startswith ('  '):
                        target = 'blank'
                    else:
                        try:
                            target = int (target)
                        except:
                            target = 0
                    _log.debug (f'Code: {event_code} -> {event_string}, Source: {station}, Target: {target}')
            # Queue Event - Incoming Call (CODE 3) -> process to queue management
                if int (station) in queues_allowed:
                    trd = Thread (target=stations.addEvent, args=(_ipecs_event, ) )
                    trd.start ()
                    return
            # Station Event -> Station LOGIN (CODE 84)
                if event_code == AGENT_IN_SERVICE:
                    trd = Thread (target=stations.addStation, args=(station, event_code, _ipecs_event['time'], ) )
                    trd.start()
            # Station/Agent LOGOUT from client (CODE 82)
                elif event_code == AGENT_OUT_OF_SERVICE:    # CODE 82
                    trd = Thread (target=stations.remove, args=(_ipecs_event, mongo, ) )
                    trd.start ()
            # Process supported events
                else:
                    trd = Thread (target=stations.addEvent, args=(_ipecs_event, ) )
                    trd.start()
            # Log event to Mongo DB
                try:
                    trd = Thread (target=mongo.logEvent, args=(_ipecs_event, False, ))
                    trd.start()
                except Exception as ex:
                    _log.error (config.getResourceString ('err', 'err008').format (ex))
            except Exception as ex:
                _log.warning (config.getResourceString ('http', 'wss016').format (ipecs_event, ex))
        else:
            # Log an error or raise exception that ipecs_event data received from server is not as expected
            err = self._config.getResourceString ('http', 'wss016').format (ipecs_event, '')
            # if fail-on-event-data-malformat flag is true, raise an exception
            if config.ipecs_fail_on_event_malformat:
                raise self.exceptions.UnknownEventFormat (err)
            else:
                # log warning and return
                _log.warning (err)
        return
# -------------------------------------------------------------------------------------------------
#   DEFINITION FOR THREADING WRAPPERS
# -------------------------------------------------------------------------------------------------
    class iPECsEventParserThread (threading.Thread):
        def __init__ (self, name: str, threadID:int, event: dict, config: ipecs_config, mongo: ipecs_db_io, stations: object, sim: bool=False):
            threading.Thread.__init__(self)
            self._log       = logging.getLogger (LOGGING_ID)
            self.threadID   = threadID
            self.name       = name
            self.event      = event
            self.config     = config
            self.mongo      = mongo
            self.stations   = stations
            self.sim        = sim

        def run (self):
            ipecsAPI.iPECsEventParser (self, self.event, self.config, self.mongo, self.stations, sim=self.sim)
    class iPECsAddEventThread (threading.Thread):
        def __init__ (self, threadID: int, name: str, event: dict , stations: object, time_format: str, mongo: ipecs_db_io):
            threading.Thread.__init__(self)
            self.threadID   = threadID
            self.name       = name
            self.event      = event
            self.station    = event['sourceNumber']
            self.code       = event['eventCode']
            self.time       = event['time']
            self.format     = time_format
            self.stations   = stations
            self.mongo      = mongo

        def run (self):
            ipecsAPI.ipecsStations.addEvent (self, self.event)
# ==================================================================================================
#   STATION STATUS CLASS DEFINITION
# ==================================================================================================
    """Class ipecsMetrics handles call related metrics such as:
    - Number of agents logged in
    - Agent Status
    - Number of active calls
    - Call related metrics

    Returns:
        [None]: [nothing]
    """
    class ipecsStations ():

    # Class Initialisation
        def __init__ (self, config: dict, station_status: dict, time_format: str, db: ipecs_db_io, call_summary: dict, agent_summary: dict, missed_call_dict: dict, acd_summary: dict, acd_history: dict, verbose=False):
            global phones_allowed
            global queues_allowed
            global station_list
            global resources
        # Definition of local variables
            self._station_list:      dict
            self._config:            dict = config
            self._calls_list:        ipecsAPI.ipecsCalls
            self._agent_summary      = agent_summary
            self._acd_summary        = acd_summary
            self._acd_history        = acd_history
            self._acd_history_temp   = self._acd_history.copy()
            self._missed_call_dict   = missed_call_dict.copy()
            self._call_summary       = call_summary
            self._time_format        = time_format
            self._station_status     = station_status
            self._log                = logging.getLogger (LOGGING_ID)
            self._mongo: ipecs_db_io = db
            self._verbose            = verbose
            self._count              = 0
            self._count_stations     = 0
            self._count_agents       = 0
            self._agents_available   = 0
            self._agents_unavailable = 0
            self._agents_busy        = 0
            self._agents_wrap        = 0
            self._agents_hold        = 0
            self._count_idle         = 0
            self._count_busy         = 0
            self._count_onhold       = 0
            self._count_wrap         = 0
            self._count_handeled     = 0
            self._count_in_queue     = 0
            self._count_active       = 0
            self._count_outbound     = 0
        # Callback Event Functions
            self._call_status_change_func:      object
            self._error_callback_func:          object
            self._call_info_func:               object
        # Create and initialise Staions object
            try:
                self._station_list = {}
                self._calls_list = ipecsAPI.ipecsCalls (cb_func=self.onCallStatusChange, 
                                                        call_hist_upd_func=self._update_acd_call_history, 
                                                        get_wrap_time_func=self._get_station_wrap_time,
                                                        db=ipecs_db_io, call_summary=self._call_summary, 
                                                        missed_call_dict=self._missed_call_dict, 
                                                        agent_summary=agent_summary, 
                                                        time_format=self._time_format)
                self._calls_list.setOnCallAnswered_Func (self._onCallAnsweredEvent)
                self._calls_list.setOnCallClosed_Func  (self._onCallDisconnectEvent)
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '__init__', ex))
    # Miscellaneous class functions
        def __len__ (self):
            return self._count
        def __del__ (self):
            try:
                if self._calls_list is not None:
                    self._calls_list.shutdown()
                if self._station_list is not None:
                    del self._station_list
                if self._agent_summary is not None:
                    del self._agent_summary
                if self._acd_summary is not None:
                    del self._acd_summary
                if self._mongo is not None:
                    del self._mongo
                if self._config is not None:
                    del self._config
            except:
                pass
        def __str__ (self):
            s = f'STATIONS: [{self._count}], idle: [{self._count_idle}], busy: [{self._count_busy}], on-hold: [{self._count_onhold}], on-wrap: [{self._count_wrap}], AGENTS: available: [{self._agents_available}], busy: [{self._agents_busy}], wrap: [{self._agents_wrap}], hold: [{self._agents_hold}]'
            return (s) 
        def shutdown (self):
            try:
                self.__del__()
            except:
                pass
        def reset_all (self) -> None:
            try:
                self._calls_list.resetCounters (stations=self._station_list)
                self._station_list.clear ()
                self._count              = 0
                self._count_stations     = 0
                self._count_agents       = 0
                self._agents_available   = 0
                self._agents_busy        = 0
                self._agents_wrap        = 0
                self._agents_hold        = 0
                self._count_idle         = 0
                self._count_busy         = 0
                self._count_onhold       = 0
                self._count_wrap         = 0
                self._count_handeled     = 0
                self._count_in_queue     = 0
                self._count_active       = 0
                self._count_outbound     = 0
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'reset_all', ex))
    # Add station / agent 
        def addStation (self, station: str, code: int, time: str) -> dict:
            global phones_allowed
            global queues_allowed
            global station_list
            global resources
        # Check is this is a queue
            if int (station) in queues_allowed:
                self._log.debug (resources['ipecs']['msg001'])
                return 
        # Register new station
            if self._find_station (station) is None:
                try:
                    # retrieve dict template 
                    tmp = self._station_status
                    tmp1 = tmp.copy()
                    try:
                        tmp1[station] = tmp1.pop('0')
                    except:
                        pass
                    rec = tmp1.copy ()
                    del tmp
                    del tmp1
                    # Create new station record
                    self._count += 1
                    if int (station) in queues_allowed:
                        rec[station]['is_queue']        = True
                    rec[station]['station']             = station
                    rec[station]['code']                = code
                    rec[station]['is_idle']             = True
                    rec[station]['agent_logged_in']     = False
                    rec[station]['station_logged_in']   = True
                    rec[station]['station_login_time']  = datetime.now()
                    self._station_list.update (rec)
                    station_list = self._station_list
                    now = datetime.now()
                    # correct any counters and only count stations, not queues
                    if int (station) >= phones_allowed[0] and int (station) <= phones_allowed[1]:
                        pay_load = {"_id": now.strftime(self._time_format) + '_' + str (station), "eventType": "station_login", "stationID": str (station), "logTime": now}
                        trd = Thread (target=self._mongo.logAgentEvent, args=(pay_load, ) )
                        trd.start()
                        self._onStationConnectedEvent ()
                    self._log.debug (resources['calls']['c001'].format (station))
                    return rec[station]
                except Exception as ex:
                    self._log.error (resources['err']['errgen'].format(self.__class__, 'addStation', ex))
                finally:
                    # Clear the record so we can reuse the object
                    del rec
            else:
                self._log.warning (resources['calls']['c018'].format(self.__class__, 'addStation'))
    # Remove station / agent
        def remove (self, event: dict, db: ipecs_db_io) -> None:
            global phones_allowed
            global queues_allowed
            station = event['sourceNumber']
            # Remove station
            if not self._find_station (station):
                self._log.warning (resources['ipecs']['wrn009'].format(station))
                return
            else:
                try:
                    # correct any counters
                    if int (station) >= phones_allowed[0] and int (station) <= phones_allowed[1]:
                        # Receive station record, update counters and signal parent
                        station_obj = self._find_station (station)
                        if station_obj is None:
                            self._log.warning (resources['calls']['c018'].format(self.__class__, 'remove'))
                        station_obj['station_logout_time']  = datetime.now()
                        station_obj['station_logged_in']   = False
                        # Update history data for this station
                        self._update_acd_stn_history (station_obj, self._acd_history)
                        # Receive station record, update counters and signal parent
                        self._onStationDisconnectedEvent (station=station_obj, notify_parent=False)
                        # Retrieve summary record template and update database with summary record
                        try:
                            now = datetime.strftime (datetime.now(), self._time_format)
                            pay_load = {"_id": now + '_' + str (station), "eventType": "station_logout", "stationID": str (station), "logTime": datetime.now()}
                            trd = Thread (target=self._mongo.logAgentEvent, args=(pay_load, ) )
                            trd.start()
                            summary = self.stationSummary (station)
                            trd_1 = Thread (target=self._mongo.logAgentSummary, args=(summary, ) )
                            trd_1.start()
                        except Exception as ex:
                            self._log.error (resources['mongo']['err024'].format (ex))
                        # Remove station from calls records list
                        self._calls_list.removeCalls (station)
                        # Remove station entry from list
                        # del self._station_list['station']
                        self._station_list.pop (station)
                        if self._count > 0:
                            self._count -= 1
                        self.onCallStatusChange ()
                        self._log.debug (resources['calls']['c002'].format (station))
                except Exception as ex:
                    self._log.error (resources['err']['errgen'].format(self.__class__, 'remove', ex))
    # Add Event Function
        def addEvent (self, event: dict) -> None:
            src = int (event['sourceNumber'])
            try:
                dest = int (event['destNumber'])
            except:
                dest = 0
            if src >= phones_allowed[0] and src <= phones_allowed[1]:
                station = str (src)
            elif dest >= phones_allowed[0] and dest <= phones_allowed[1]:
                station = str (dest)
            elif src in queues_allowed:
                station = str (src)
            else:
                return
            code    = int (event['eventCode'])
            time    = event['time']
            try:
            # Is it a queue related event?
                if code in [QUEUE_BUSY, QUEUE_IDLE, QUEUE_INCOMING_CALL]:
                    # TODO: Queue is busy, for now ignore this
                    if code == QUEUE_BUSY:
                        return
                    if code is QUEUE_IDLE:
                        if self._calls_list.findQueueObject (call_id=int (event['callRefID'])) is not None:
                            self._calls_list.removeCallFromQueue (call_id=int (event['callRefID']), event_code=QUEUE_IDLE)
                    if code is QUEUE_INCOMING_CALL:
                        self._calls_list.addCallToQueue (call_id=int (event['callRefID']))
                # Check if the station is already in the state signalled in the event
                elif self._find_record (station, code):
                    # No change - return without doing anything
                    return
            # Register new station
                rec = self._find_station (station)
                # There is no record for this station - this can happen if the wrapper restarts and there are still phones and agents logged in.
                # To counter this situation, the station object needs to be created and if specific events are triggering this, 
                # we can assume that the agent is also logged into the ACD; therefore, we also need to trigger the agent ACD logged in process.
                if rec is None:
                    rec = self.addStation (station, code, time)
                    if rec is not None:
                        # The following codes will only be received, if an agent is logged into ACD.
                        # Therefore signal that the station is connected and the agent is logged in
                        if code in [41, 42, 43, 44, 49, 50, 57, 62, 66, 67, 71, 72] and not rec['agent_available']:
                            self._onStationConnectedEvent ()
                            self._onAgentLoggedInEvent  (rec)
                            self._onAgentAvailableEvent (rec)
                            self._log.debug (resources['calls']['c006'].format (station))
                # update the event code
                else:
                    rec['code'] = code
            # Agent logs in via ACD (CODE 11)
                    if code == AGENT_ACD_LOGIN:
                        if not rec['agent_logged_in']:
                            self._onAgentLoggedInEvent (rec)
                            self._log.debug (resources['calls']['c004'].format (station))
                            self._station_list[station].update (rec)
                        else:
                            return
            # Agent logs out of ACD (Code 12)
                if code == AGENT_ACD_LOGOUT:
                    if rec['agent_logged_in']:
                        self._onAgentLoggedOutEvent (rec)
                        try:
                            data = self.stationSummary (station)
                            self._update_acd_stn_history (data['station'])
                            trd = Thread (target=self._mongo.logAgentSummary, args=(data, ) )
                            trd.start()
                            # asyncio.ensure_future (self._mongo.logAgentSummary (pay_load=data))
                        except:
                            pass
                        self._log.debug (resources['calls']['c005'].format (station))
                    else:
                        return
            # Agent unavailable in ACD (Code 13)
                elif code == AGENT_ACD_UNAVAIL:
                    if rec['agent_available']:
                        self._onAgentUnavailableEvent (rec)
                        self._log.debug (resources['calls']['c007'].format (station))
                    else:
                        return
            # Agents available via ACD (Code 14)
                elif code == AGENT_ACD_AVAIL:
                    if not rec ['agent_available']:
                        self._onAgentAvailableEvent (rec)
                        self._log.debug (resources['calls']['c006'].format (station))
                    else:
                        return
            # Agent ACD Wrap start (Code 15)
                elif code == AGENT_ACD_WUP_START:
                    self._onAgentWrapUpStartEvent (rec)
                    self._log.debug (resources['calls']['c016'].format (station))
                    return
            # Agent ACD Wrap end (Code 16)
                elif code == AGENT_ACD_WUP_END:
                    self._onAgentWrapUpEndEvent (rec)
                    self._log.debug (resources['calls']['c017'].format (station))
                    return
            # Station going into busy status (Code 17)
                elif code == STATION_BUSY and int (station) >= phones_allowed[0] and int (station) <= phones_allowed[1]:
                    if rec['is_busy']:
                        return
                    else:
                        self._onStationBusyEvent (rec)
                        self._log.debug (resources['calls']['c008'].format (station))
            # Agent ACD Wrap end (Code 19)
                elif code == STATION_DND_ACTIVE:
                    self._onAgentUnavailableEvent (rec)
                    self._log.debug (resources['calls']['c017'].format (station))
                    return
            # Station going into idle state (Code 18)
                elif code == STATION_IDLE and int (station) >= phones_allowed[0] and int (station) <= phones_allowed[1]:
                    # If station is already idle just return
                    if rec['is_idle']:
                        return
                    self._onStationIdleEvent (rec)
                    self._log.debug (resources['calls']['c010'].format (station))
            # Station going into busy status (Code 20)
                elif code == STATION_DND_INACTIVE:
                        self._onAgentAvailableEvent (rec)
                        self._log.debug (resources['calls']['c006'].format (station))
            # Station is ringing (Code 66)
                elif code == STATION_RINGING and rec is not None:
                    if rec['is_ringing']:
                        return
                    else:
                        self._onCallWaitingEvent (rec=rec)
            # Station is initiating an outbound call (CODE 67)
                elif code == OUTBOUND_CALL:
                    self._onOutboundCall (rec)
            # SMDR summary of call (CODE 69) -> this will arrive after a outbound call is ended
                elif code == SMDR_CALL_SUMMARY:
                    self._onOutboundCallClosed (rec)
                    # Check that Data1 contains 'HHMMSS'
                    if len (event['data1']) == 6:
                        self.addSMDREvent (event)
                        # asyncio.ensure_future (self._mongo.logSMDREvent (event))
                        trd = Thread (target=self._mongo.logSMDREvent, args=(event, ) )
                        trd.start()
                    else:
                        self._log.warning (self._config.getResourceString ('ipecs','wrn008'))
            # Call related Events
            #       STATION_RINGING, STATION_SEIZED, AGENT_ACD_WUP_START, AGENT_ACD_WUP_END,
            #       STATION_CONNECTED, STATION_ANSWERED, STATION_ON_HOLD, ACD_ON_HOLD, STATION_OFF_HOLD,
            #       STATION_OFF_HOLD, STATION_ABANDONED, STATION_DISCONNECTED, OUTBOUND_CALL
                elif code in [18, 19, 20, 41, 42, 43, 44, 49, 50, 57, 62, 66, 67, 71, 72]:
                    inq = False
                    direction = DIR_INBOUND
                    did = ''
                    if int (station) in queues_allowed:
                        inq = True
                    if code == OUTBOUND_CALL:
                        direction = DIR_OUTBOUND
                        try:
                            s = str (event['data2'])
                            s.index ('  ')
                            did = None
                        except:
                            did = event['data2']
                    elif code == DID_INFO_INCOMING or CALLER_INF_INCOMING:
                        try:
                            str (event['data1']).index ('  ')
                            did = None
                        except:
                            did = str (event['data1'])
                        try:
                            # Since iPECs sends several notifications about an incoming call we need to filter our and only 
                            # react to the first event that signals a STATION is ringing.
                            # To do this, we first check if there already is a call object in existence
                            call = self._calls_list.find (call_id=event['callRefID'])
                            # If there is no call object, this event is a call placed in queue - aka NEW call
                            if call is None:
                                # Since there is no call object, we now place the call into queue to signal that there is a call waiting in queue
                                self._calls_list.addCallerIDToQueue (call_id=int(event['callRefID']), caller_id=did)
                                # Notify dashboard app that there is a call status change -> update dashboard
                                self.onCallStatusChange ()
                            else:
                                # There is a call object in existence, we now need to check if the call notification has been sent and if not, 
                                # then we need to notify the main app that there is a call ringing on a specific station
                                if not call.notification_sent and did is not None and did.isnumeric():
                                    # Notify main app of incoming call
                                    self._call_info_func (station_id=station, call_id=event['data1'], time_stamp=event['time'])
                                    call.notification_sent = True
                        except Exception as ex:
                            self._log.error (f'{self.__class__}.addEvent -> {ex}')
                    # The next Try/Exception is necessary as some events do not have the callRefId in their dictionary !!!!!
                    try:
                        call = self._calls_list.find (call_id=int (event['callRefID']))
                    except:
                        call = self._calls_list.find (call_id=int (station))
                    if call is None:
                        call = self._calls_list.append (call_id=int(event['callRefID']), station=int(station), event=code, in_queue=inq, call_dir=direction, did=did)
                    # Filter out multiple and repeated call in queue events for the same call
                    else:
                        if call.call_ID == int(event['callRefID']) and call.station_ID == station and call.inQueue and code == QUEUE_INCOMING_CALL:
                            return
                        else:
                            if call.call_Direction == DIR_OUTBOUND:
                                self._calls_list.update (call_id=int(event['callRefID']), station=int(station), event=code, did=did)
                            else:
                                self._calls_list.update (call_id=int(event['callRefID']), station=int(station), event=code, in_queue=inq, call_dir=direction, did=did)
                if self._verbose:
                    self._log.debug (resources['calls']['c011'].format (event))
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'addEvent', ex))
    # Return station list
        def get_stations (self) -> dict:
            return self._station_list
    # Add SMDR Event
        def addSMDREvent (self, event_data: dict) -> None:
            pass
        #TODO: Write data to mongo db
                #ts = event_data['data1']
                #hrs  = int (ts[0]) * 10 + int (ts[1])
                #mins = int (ts[2]) * 10 + int (ts[3])
                #secs = int (ts[4]) * 10 + int (ts[5])
                # Convert from hh:mm:ss to seconds
                #h_time = hrs * 3600 + mins * 60 + secs
                # Notify Subscriber
    # Properties and Methods
        @property
        def station_status (self) -> dict:
            return self._station_list
        @property
        def station_idle_count (self) -> int:
            return self._count_idle
        @property
        def station_busy_count (self) -> int:
            return self._count_busy
        @property
        def station_hold_count (self) -> int:
            return self._count_onhold
        @property
        def calls_handled (self) -> int:
            return self._count_handeled
        @property
        def getStationList (self) -> list:
            if self._count > 0:
                stations: list = []
                for key in self._station_list.keys():
                    stations.append (key)
                return stations
            return None
        def _get_station_wrap_time (self, station:str) -> float:
            _station = self._find_station (station)
            if _station is None:
                return 0.0
            else:
                return _station['total-wrap-time']
    # Get ACD Summary
        def getACDSummary (self, all_data:bool = True) -> dict:
            """Creates and returns a dictionary of acd-summary

            Returns:
                Dictionary:     {   "stations-connected":   0,
                                    "agents-logged-in":     0,
                                    "total-inbound-calls":  0,
                                    "total-answered-calls": 0,
                                    "total-abandoned-calls":0,
                                    "total-outbound-calls": 0,
                                    "total-logged-in-time": '',
                                    "total-avail-time":     0.0,
                                    "total-unavail-time":   0.0,
                                    "total-idle-time":      0.0, 
                                    "total-busy-time":      0.0,
                                    "total-hold-time":      0.0,
                                    "total-wrap-time":      0.0
                                }
            """
        # Reset counters
            try:
                if len (self._station_list) > 0 or len (self._calls_list) > 0:
                # Set everything to 0
                    self.reset_acd_summary ()
                # Get current counters
                    self._acd_summary['stations-connected']    = self._count_stations
                    self._acd_summary['stations-idle']         = self._count_idle
                    self._acd_summary['stations-busy']         = self._count_busy
                    self._acd_summary['agents-busy']           = self._agents_busy
                    self._acd_summary['agents-idle']           = self._agents_available - self._agents_busy
                    self._acd_summary['agents-logged-in']      = self._count_agents
                    self._acd_summary['agents-available']      = self._agents_available
                    self._acd_summary['agents-unavailable']    = self._count_agents - self._agents_available
                    self._acd_summary['total-inbound-calls']   = self._calls_list.calls_inbound
                    self._acd_summary['total-answered-calls']  = self._calls_list.calls_answered
                    self._acd_summary['total-outbound-calls']  = self._calls_list.calls_outbound
                    self._acd_summary['total-calls-in-queue']  = self._calls_list.calls_in_queue
                    self._acd_summary['total-abandoned-calls'] = self._calls_list.calls_abandoned
                    self._acd_summary['total-calls-onhold']    = self._calls_list.calls_on_hold
                # Update times from each connected station
                    if not (self._config['status-calls-only']) or all_data:
                        for key in self._station_list.keys():
                            # Do not count events that are queue related
                            #if int (key) in self._queues_allowed:
                            #    continue
                            # ====================================
                            if int (key) in queues_allowed:
                                continue
                            stn = self._station_list[key]
                            now = datetime.now()
                        # Calculate elapsed login time for Station
                            if stn['station_login_time'] is not None and isinstance (stn['station_login_time'], datetime) and stn['station_logged_in']:
                                dt = (now - self._station_list[key]['station_login_time']).total_seconds()
                                self._acd_summary['total-logged-in-time'] += round (dt, 0)
                        # Calculate elapsed login time for Agent
                            if stn['agent_login_time'] is not None and isinstance (stn['agent_login_time'], datetime) and stn['agent_logged_in']:
                                dt = (now - self._station_list[key]['agent_login_time']).total_seconds()
                                self._acd_summary['total-agn-login-time'] += round (dt, 0)
                        # Calculate agent idle times
                            # if stn['idle_start_time'] != '' and stn['is_idle'] and stn['agent_logged_in']:
                            #    dt = (now - self._station_list[key]['idle_start_time']).total_seconds()
                            #    self._acd_summary['total-idle-time'] += round(dt, 0)
                            #else:
                            #    self._acd_summary['total-idle-time'] += round (stn['total-idle-time'], 0)
                            self._acd_summary['total-idle-time']     += round (stn['total-idle-time'], 0)
                            self._acd_summary['total-avail-time']    += round (stn['total-avail-time'], 0)
                            self._acd_summary['total-unavail-time']  += round (stn['total-unavail-time'], 0)
                            self._acd_summary['total-busy-time']     += round (stn['total-busy-time'], 0)
                            self._acd_summary['total-hold-time']     += round (stn['total-hold-time'], 0)
                            self._acd_summary['total-wrap-time']     += round (stn['total-wrap-time'], 0)
                # Add times from previously logged in stations
                        if all_data:
                            self._acd_summary['total-logged-in-time'] += self._acd_history['total-logged-in-time']
                            self._acd_summary['total-idle-time']      += self._acd_history['total-idle-time']
                            self._acd_summary['total-avail-time']     += self._acd_history['total-avail-time']
                            self._acd_summary['total-unavail-time']   += self._acd_history['total-unavail-time']
                            self._acd_summary['total-busy-time']      += self._acd_history['total-busy-time']
                            self._acd_summary['total-hold-time']      += self._acd_history['total-hold-time']
                            self._acd_summary['total-wrap-time']      += self._acd_history['total-wrap-time']
                            self._acd_summary['station-list']         = self.getStationList
                    return self._acd_summary
                else:
                    return None
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'getACDSummary', ex))
    # Find record function    
        def _find_record (self, station: str, code: int) -> bool:
            try:
                for key in self._station_list.keys():
                    if key == station:
                        if self._station_list[key]['code'] == code:
                            return True
                        return False
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_find_record', ex))
    # Return station object function
        def _find_station (self, station: str) -> dict:
            try:
                for key in self._station_list.keys():
                    if key == station:
                        return self._station_list[key]
                return None
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_find_station', ex))
        def findStation (self, station) -> dict:
            return self._find_station (station)
    # Compile station summary including call data
        def stationSummary (self, station) -> dict:
            try:
                # First get summary of call information
                stn = self._find_station (station)
                if stn is not None:
                    ss = self._calls_list.summaryOfCallsByStation (station, self._agent_summary)
                    if ss is not None:
                        if stn['station_login_time'] is not None and isinstance (stn['station_login_time'], datetime) and stn['station_logout_time'] is not None and isinstance (stn['station_logout_time'], datetime):
                            stn['total-logged-in-time'] = round ((stn['station_logout_time'] - stn['station_login_time']).total_seconds(), 0)
                        if stn['agent_login_time'] is not None and isinstance (stn['station_login_time'], datetime) and stn['agent_logout_time'] is not None and isinstance (stn['agent_logout_time'], datetime):
                            stn['total-agn-login-time'] = round ((stn['agent_logout_time'] - stn['agent_login_time']).total_seconds(), 0)
                        # Now fill in the rest for the data to form the picture of the agents performance
                        ss['station']               = int (station)
                        ss['date']                  = datetime.now().strftime('%Y-%m-%d')
                        ss['time']                  = datetime.now().strftime('%H:%M:%S')
                        ss['login-time']            = stn['station_login_time']
                        ss['logout-time']           = stn['agent_logout_time']
                        ss['avail_start_time']      = stn['agent_login_time']
                        ss['total-calls']           = stn['total-inbound-calls']
                        ss['answered-calls']        = stn['total-answered-calls']
                        ss['abandoned-calls']       = stn['total-abandoned-calls']
                        ss['outbound-calls']        = stn['total-outbound-calls']
                        ss['total-logged-in-time']  = stn['total-logged-in-time']
                        ss['total-agn-login-time']  = stn['total-agn-login-time']
                        ss['total-avail-time']      = stn['total-avail-time']
                        ss['total-unavail-time']    = stn['total-unavail-time']
                        ss['total-idle-time']       = stn['total-idle-time']
                        ss['total-busy-time']       = stn['total-busy-time']
                        ss['total-hold-time']       = stn['total-hold-time']
                        ss['total-wrap-time']       = stn['total-wrap-time']
                        ss['total-ring-time']       = stn['total-ring-time']
                        ss['total-talk-time']       = stn['total-talk-time']
                        ss['total-handle-time']     = stn['total-handle-time']
                        # Remove all calls belonging to that station from the calls list
                        self._calls_list.removeCalls (station)
                    return ss
                else:
                    return None
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'stationCallSummary', ex))
    # Reset Station Values
        def reset_acd_summary (self, reset_calls: bool = False) -> None:
            """Function resets all counter values to 0
            """
            try:
                self._acd_summary['total-inbound-calls']    = 0
                self._acd_summary['total-answered-calls']   = 0
                self._acd_summary['total-abandoned-calls']  = 0
                self._acd_summary['total-outbound-calls']   = 0
                self._acd_summary['total-logged-in-time']   = 0.0
                self._acd_summary['total-avail-time']       = 0.0
                self._acd_summary['total-unavail-time']     = 0.0
                self._acd_summary['total-idle-time']        = 0.0
                self._acd_summary['total-busy-time']        = 0.0
                self._acd_summary['total-hold-time']        = 0.0
                self._acd_summary['total-wrap-time']        = 0.0
                self._acd_summary['total-ring-time']        = 0.0
                self._acd_summary['total-talk-time']        = 0.0
                self._acd_summary['total-handle-time']      = 0.0
                if reset_calls:
                    # Reset the calls as well
                    self._calls_list.clear()
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'reset_acd_summary', ex))
    # Reset ACD History/ Temporary data
        def reset_acd_hist_data (self, hist_data: dict) -> None:
            try:
                for key in hist_data.keys():
                    hist_data[key] = 0.0
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'reset_acd_hist_data', ex))
    # Update ACD CALL History
        def _update_acd_call_history (self, call: object, target: dict=None) -> None: #XXX
            try:
                _target = target
                if _target is None:
                    _target = self._acd_history
                if _target is not None and call is not None:
                    _target['total-hold-time']    += call.hold_time
                    _target['total-ring-time']    += call.ring_time
                    _target['total-talk-time']    += call.talk_time
                    _target['total-handle-time']  += call.talk_time + call.hold_time
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_update_acd_call_history', ex))
    # Update ACD STATION History
        def _update_acd_stn_history (self, station: dict, target: dict=None) -> None:
            try:
                _target = target
                if _target is None:
                    _target = self._acd_history
                if _target is not None and station is not None:
                    _target['total-wrap-time'] += station['total-wrap-time']
                    if isinstance (station['station_logout_time'], datetime):
                        _target['total-logged-in-time'] += (station['station_logout_time'] - station['station_login_time']).total_seconds ()
                    else:
                        _target['total-logged-in-time'] += (datetime.now() - station['station_login_time']).total_seconds ()
                    if isinstance (station['agent_logout_time'], datetime):
                        _target['total-agn-login-time'] += (station['agent_logout_time'] - station['agent_login_time']).total_seconds () + station['total-agn-login-time']
                    else:
                        _target['total-agn-login-time'] += (datetime.now() - station['agent_login_time']).total_seconds () + station['total-agn-login-time']
                    _target['total-avail-time']     += station['total-avail-time']
                    _target['total-unavail-time']   += station['total-unavail-time']
                    _target['total-idle-time']      += station['total-idle-time']
                    _target['total-busy-time']      += station['total-busy-time']
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_update_acd_stn_history', ex))
    # GetCallStats
        def getCallStats (self) -> dict:
            return self._calls_list.getCallStats()
    # Get Agents Statistics
        def getAgentStats (self) -> dict:
            try:
                data  = self._acd_history_temp
                now = datetime.now()
                metrics = {}
                if len (self._calls_list) > 0:
                    for call in self._calls_list:
                        self._update_acd_call_history (call=call, target=data)
                if len (self._station_list) > 0:
                    for station in self._station_list:
                        _station = self._find_station (station)
                        self._update_acd_stn_history (self._find_station (station), data)
                        # The following code calculates the login times up to current.
                        # This is required as the timestamps and calculation will normally only happen after agent or station logs out.
                        if _station['total-logged-in-time'] <= 0.0 and isinstance (_station['station_login_time'], datetime):
                            data['total-logged-in-time'] += round ((now - _station['station_login_time']).total_seconds(), 0)
                        if _station['total-agn-login-time'] <= 0.0 and isinstance (_station['agent_login_time'], datetime):
                            data['total-agn-login-time'] += round ((now - _station['agent_login_time']).total_seconds(), 0)
                        if _station['agent_available'] and isinstance (_station['avail_start_time'], datetime):
                            data['total-avail-time'] += _station['total-avail-time'] + round ((now - _station['avail_start_time']).total_seconds(), 0)
                if data is not None:
                    availability: float = 0.0
                    utilisation:  float = 0.0
                    work_time:    float = round (data['total-wrap-time'] + data['total-busy-time'], 0)
                    if data['total-logged-in-time'] is not None and data['total-logged-in-time'] > 0.0:
                        availability = round ((data['total-agn-login-time'] - data['total-unavail-time']) / data['total-logged-in-time'], 2)
                    if data['total-agn-login-time'] is not None and data['total-agn-login-time'] > 0.0:
                        utilisation = round (work_time / data['total-agn-login-time'], 2)
                    metrics = {
                        "Total Phone Login Time":   data['total-logged-in-time'],
                        "Total Agent Login Time":   data['total-agn-login-time'],
                        "Total Available Time":     data['total-avail-time'],
                        "Total Unavailable Time":   data['total-unavail-time'],
                        "Total Active Time":        data['total-busy-time'],
                        "Total Idle Time":          data['total-idle-time'],
                        "Total Wrap Time":          data['total-wrap-time'],
                        "Availability":             availability,
                        "Utilisation":              utilisation
                    }
                return metrics
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'getAgentStats', ex))
            finally:
                self.reset_acd_hist_data (self._acd_history_temp)
# -------------------------------------------------------------------------------------------------
#   STATIONS CLASS DEFINITION FOR CALLBACK HOOKS
# ------------------------------------------------------------------------------------------------- 
        def addEventHook (self, function: object) -> None:
            if function is not None:
                self._call_status_change_func = function
        def addCallDisconnectedHook (self, function: object) -> None:
            if function is not None:
                self._call_disconnected_func = function
        def addCallAnsweredHook (self, function: object) -> None:
            if function is not None:
                self._call_answered_func = function
        def addCallRingingHook (self, function: object) -> None:
        # Expects 2 parameters - call_id and station_id
            if function is not None:
                self._call_info_func = function
    # Main Callback function to parent
        def onCallStatusChange (self) -> None:    
            if self._call_status_change_func is not None:
                self._call_status_change_func (self.getACDSummary())
# -------------------------------------------------------------------------------------------------
#   STATIONS CLASS DEFINITION FOR CALLBACK FUNCTIONS
# -------------------------------------------------------------------------------------------------
        def _onStationIdleEvent (self, rec: dict) -> None:
            try:
                now = datetime.now()
                rec['idle_start_time']  = now
                rec['is_busy']          = False
                rec['is_ringing']       = False
                rec['is_hold']          = False
                rec['is_wrap']          = False
                rec['is_on_call_out']   = False
                rec['is_on_call_in']    = False
                if rec['busy_start_time'] != '':
                    # tl = datetime.strptime (rec['busy_start_time'], self._time_format)
                    td = now - rec['busy_start_time']
                    rec['total-busy-time'] += round (td.total_seconds(), 0)
                    if self._count_busy > 0:
                        self._count_busy -= 1
                if self._count_stations > self._count_idle and not rec['is_idle']:
                    self._count_idle += 1
                rec['is_idle'] = True
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onStationIdleEvent', ex))
            self.onCallStatusChange ()
        def _onStationBusyEvent (self, rec: dict) -> None:
            try:
                now = datetime.now()
                rec['busy_start_time']  = now
                rec['is_busy']          = True
                rec['is_idle']          = False
                rec['is_ringing']       = False
                rec['is_hold']          = False
                rec['is_wrap']          = False
                self._count_busy        += 1
                if rec['idle_start_time'] != '':
                    # tl = datetime.strptime (rec['idle_start_time'], self._time_format)
                    td = now - rec['idle_start_time']
                    rec['total-idle-time'] += round (td.total_seconds(), 0)
                    if self._count_idle > 0:
                        self._count_idle -= 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onStationBusyEvent', ex))
            self.onCallStatusChange ()
        def _onStationConnectedEvent (self) -> None:
            # Increase station counters
            self._count_stations += 1
            if self._count_stations > self._count_idle:
                self._count_idle += 1
            self.onCallStatusChange ()
        def _onStationDisconnectedEvent (self, station: dict, notify_parent=True) -> None:
            try:
                if self._count_stations > 0:
                    self._count_stations -= 1
                if station is not None:
                    if station['is_idle'] and self._count_idle > 0:
                        self._count_idle -= 1
                    if station['is_busy'] and self._count_busy > 0:
                        self._count_busy -= 1
                    if station['is_hold'] and self._count_onhold > 0:
                        self._count_onhold -= 1
                    if station['is_wrap'] and self._count_wrap > 0:
                        self._count_wrap -= 1
                    if station['agent_logged_in'] and self._count_agents > 0:
                        self._count_agents -= 1
                if notify_parent:
                    self.onCallStatusChange ()
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onStationDisconnectedEvent', ex))
        def _onCallDisconnectEvent (self, station_id: int) -> None:
            try:
                if self._agents_busy > 0:
                    self._agents_busy -= 1
                #if self._agents_available < self._count_agents:
                #    self._agents_available += 1
                rec = self._find_station (station_id)
                if rec is not None and isinstance (rec['busy_start_time'], datetime):
                    rec['total_busy_time'] = round ((datetime.now() - rec['busy_start_time']).total_seconds(), 0)
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallDisconnectEvent', ex))
            self.onCallStatusChange ()
        def _onCallAnsweredEvent (self, station_id: int) -> None:
            try:
                #if self._agents_available > 0:
                #    self._agents_available -= 1
                if self._agents_busy < self._agents_available:
                    self._agents_busy += 1
                rec = self._find_station (station_id)
                if rec is not None:
                    rec['busy_start_time'] = datetime.now()
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallAnsweredEvent', ex))
            self.onCallStatusChange ()
        def _onCallWaitingEvent (self, rec: dict) -> None:
            try:
                if rec is not None:
                    now = datetime.now()
                    rec['ringing_start_time'] = now.strftime (self._time_format)
                    rec['is_ringing']         = True
                    rec['is_idle']            = False
                    rec['is_busy']            = False
                    rec['is_hold']            = False
                    rec['is_wrap']            = False
                    rec['is_on_call_out']     = False
                    rec['is_on_call_in']      = False
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallWaitingEvent', ex))
            self.onCallStatusChange ()
        def _onOutboundCall (self, rec: dict) -> None:
            try:
                if rec is not None:
                    rec['is_on_call_out']   = True
                    rec['is_busy']          = True
                    if self._agents_busy < self._count_agents:
                        self._agents_busy += 1
                    if self._count_busy < self._count:
                        self._count_busy += 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onOutboundCall', ex))
            self.onCallStatusChange ()
        def _onOutboundCallClosed (self, rec: dict) -> None:
            try:
                if rec is not None:
                    rec['is_busy']        = False
                    rec['is_on_call_out'] = False
                    if self._agents_busy > 0:
                        self._agents_busy -= 1
                    if self._count_busy > 0:
                        self._count_busy -= 1
                    self._count_outbound += 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onOutboundCallClosed', ex))
            self.onCallStatusChange ()
        def _onAgentLoggedInEvent (self, rec: dict) -> None:
            try:
                if rec is not None:
                    if rec['agent_logged_in']:
                        return
                    # now = datetime.strftime (, self._time_format)
                    now = datetime.now()
                    self._count_agents       += 1
                    if self._agents_available < self._count_agents:
                        self._agents_available += 1
                    rec['code']              = AGENT_ACD_LOGIN
                    rec['is_idle']           = True
                    rec['agent_logged_in']   = True
                    rec['agent_available']   = True
                    rec['avail_start_time']  = now
                    rec['agent_login_time']  = now
                    pay_load = {"_id": now.strftime(self._time_format) + '_' + str (rec['station']), "eventType": "agent_login", "stationID": rec['station'], "logTime": now}
                    trd = Thread (target=self._mongo.logAgentEvent, args=(pay_load, ))
                    trd.start()
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onAgentLoggedInEvent', ex))
            self.onCallStatusChange ()
        def _onAgentLoggedOutEvent (self, rec: dict) -> None:
            try:
                if rec is not None:
                    if not rec['agent_logged_in']:
                        return
                    now = datetime.now()
                    rec['code'] = AGENT_ACD_LOGOUT
                    if self._agents_available > 0 and rec['agent_available']:
                        self._agents_available -= 1
                    if self._count_agents > 0: 
                        self._count_agents -= 1
                    if self._agents_unavailable > 0 and rec['agent_unavailable']:
                        self._agents_unavailable -= 1
                    # Calculate total time agent was logged into ACD
                    if rec['agent_login_time'] is not None and isinstance (rec['agent_login_time'], datetime):
                        td = round ((now - rec['agent_login_time']).total_seconds(), 0) #XXX
                        rec['total-agn-login-time'] = td
                        self._acd_history ['total-agn-login-time'] += td
                    # Calculate total time agent was available - this a bit more tricky, as the agent might have gone into DND during login time
                    # so, need to see if there is a value in total available time and then need to add the last value of now - available-start-time 
                    if rec['avail_start_time'] is not None and isinstance (rec['avail_start_time'], datetime):
                        td = round ((now - rec['avail_start_time']).total_seconds(), 0)
                        # Ad the delta to any existing time
                        rec['total-avail-time'] += td
                        # update history record
                        self._acd_history ['total-avail-time'] += rec['total-avail-time']
                    rec['agent_logout_time'] = now
                    rec['agent_logged_in']   = False
                    rec['agent_available']   = False
                    rec['agent-unavailable'] = True
                    rec['agent-busy']        = False
                    pay_load = {"eventType": "agent_logout", "stationID": rec['station'], "logTime": now}
                    trd = Thread (self._mongo.logAgentEvent, (pay_load, ) )
                    trd.start()
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onAgentLoggedOutEvent', ex))
            # Call and update parent function
            self.onCallStatusChange ()
        def _onAgentAvailableEvent (self, rec: dict) -> None:
            try:
                if rec is not None:
                    # Filter out the curious behavior of iPECs API to sent an agent is idle event before sending agent is unavailable.
                    if rec['agent_available']:
                        return
                    now = datetime.now()
                    if rec['unavail_start_time'] is not None:
                        td = now - rec['unavail_start_time']
                        rec['total-unavail-time'] += round (td.total_seconds(), 0)
                        rec['unavail_start_time'] = None
                    if self._agents_available < self._count_agents:
                        self._agents_available += 1
                    if self._agents_unavailable > 0 and rec['agent_unavailable']:
                        self._agents_unavailable -= 1
                    rec['agent_available'] = True
                    rec['agent_unavailable'] = False
                    rec['avail_start_time'] = now
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onAgentAvailableEvent', ex))
            self.onCallStatusChange ()
        def _onAgentUnavailableEvent (self, rec: dict) -> None:
            try:
                if rec is not None:
                    if not ['agent_available']:
                        return
                    now = datetime.now()
                    if self._agents_unavailable < self._count_agents and rec['agent_available']:
                        self._agents_unavailable += 1
                    if self._agents_available > 0:
                        self._agents_available -= 1
                    rec['agent_available']    = False
                    rec['agent_unavailable']  = True
                    rec['unavail_start_time'] = now
                    if rec['avail_start_time'] is not None and isinstance (rec['avail_start_time'], datetime):
                        td = now - rec['avail_start_time']
                        rec['total-avail-time'] += round (td.total_seconds(), 0)
                        rec['avail_start_time'] = None
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onAgentUnavailableEvent', ex))
            self.onCallStatusChange ()
        def _onAgentWrapUpStartEvent (self, rec: dict) -> None:
            try:
                if not rec is None and not rec['agent_wrap_up']:
                    rec['code'] = AGENT_ACD_WUP_START
                    rec['agent_wrap_up'] = True
                    rec['wup_start_time'] = datetime.now()
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onAgentWrapUpStartEvent', ex))
        def _onAgentWrapUpEndEvent (self, rec: dict) -> None:
            try:
                if not rec is None and rec['agent_wrap_up']:
                    now = datetime.now()
                    rec['code'] = AGENT_ACD_WUP_END
                    if rec['wup_start_time'] is not None and isinstance (rec['wup_start_time'], datetime):
                        rec['total-wrap-time'] += round ((now - rec['wup_start_time']).total_seconds(), 0)
                        rec['wup_start_time'] = None
                    rec['agent_wrap_up'] = False
                if self._agents_busy > 0 and rec['agent_busy']:
                    self._agents_busy -= 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onAgentWrapUpEndEvent', ex))
# -------------------------------------------------------------------------------------------------
#                   DEFINITION FOR CLASS TESTS
# -------------------------------------------------------------------------------------------------
        def runAPItests (self):
            # Manual tests of threads...
            #self._onCallAnsweredEvent ()
            print ('Running iPECs API self test...\n\n')
            #self._onCallDisconnectEvent ()
            self._onStationConnectedEvent ()
            print ('iPECs API self tests concluded\n\n')
# ==================================================================================================
#   CALLS CLASS DEFINITION
# ==================================================================================================
    class ipecsCalls ():
        global queues_allowed
        global phones_allowed
    # Calls Class Variable Declarations
        # Declaration of Local variables
        _calls:              list
        _queue_list:         list
        _call_summary_dict:  dict
        _agt_summary_dict:   dict
        _callback_func:      object
        _oncall_ans_func:    object
        _oncall_closed_func: object
        _upd_hist_func:      object
        _get_wrp_tm_func:    object
        _index:              int
        _log:                logging.Logger
        # Declaration of Call Count related Variables
        _calls_abandoned:    int
        _calls_active:       int
        _calls_answered:     int
        _calls_in_queue:     int
        _calls_in_wrap:      int
        _calls_on_hold:      int
        _calls_ringing:      int
        _calls_inbound:      int
        _calls_outbound:     int
        # Declaration of Time related variables
        _queue_time:         float
        _total_talk_time:    float
        _total_hold_time:    float
        _total_out_time:     float
        _total_ring_time:    float
        _total_wrap_time:    float
        _total_handle_time:  float
    # Calls Class Intialisation Function
        def __init__ (self, cb_func: object, call_hist_upd_func: object, get_wrap_time_func: object, db: ipecs_db_io, call_summary: dict, missed_call_dict: dict, agent_summary: dict, time_format: str) -> None:
        # Global variables
            global resources
        # Set Local variables
            self._callback_func     = cb_func
            self._upd_hist_func     = call_hist_upd_func
            self._get_wrp_tm_func   = get_wrap_time_func
            self._mongo:ipecs_db_io = db
            self._agt_summary_dict  = agent_summary
            self._call_summary_dict = call_summary
            self._missed_call_dict  = missed_call_dict
            self._log               = logging.getLogger (LOGGING_ID)
            self._calls: list       = []
            self._queue_list: list  = []
            self._queue_time        = 0.0
            self._time_format       = time_format
            self._index             = 0
        # Set Call Cont variables
            self._calls_abandoned   = 0
            self._calls_active      = 0
            self._calls_answered    = 0
            self._calls_in_queue    = 0
            self._calls_in_wrap     = 0
            self._calls_on_hold     = 0
            self._calls_ringing     = 0
            self._calls_inbound     = 0
            self._calls_outbound    = 0
            self._log               = logging.getLogger (LOGGING_ID)
        # Set Time related variables
            self._total_talk_time   = 0.0
            self._total_hold_time   = 0.0
            self._total_out_time    = 0.0
            self._total_ring_time   = 0.0
            self._total_wrap_time   = 0.0
            self._total_handle_time = 0.0
        def __len__ (self) -> int:
            return len (self._calls) + len (self._queue_list)
        def __del__ (self) -> None:
            try:
                if isinstance (self._calls, list):
                    for call in self._calls:
                        del call
                        del self._calls
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '__del__', ex))
        def __iter__(self):
            """Returns the Iterator object"""
            return iter (self._calls)
        def __next__(self):
            """Returns the next value from ipecsCalls object's lists"""
            if self._index < len(self._calls) :
                result = (self._calls[self._index])
                self._index +=1
                return result
    # Calls Class Shutdown
        def shutdown (self):
            try:
                self.__del__()
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'shutdown', ex))
    # QUEUE ADD CALL to call queue
        def addCallToQueue (self, call_id: int) -> None:
            try:
                # Check if call_id is already in queue list
                q_obj = self.findQueueObject (call_id)
                if q_obj is None:
                    q_obj = {"id": call_id, "caller_id": "", "times": {"ring_start": datetime.now()}}
                    self._queue_list.append (q_obj)
                    self._onCallInQueue ()
                return
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'addCallToQueue', ex))
    # QUEUE CLEAR ALL CALLS from call queue
        def clearCallQueue (self):
            try:
                if len (self._queue_list) > 0:
                    for i in range (len (self._queue_list), 0, -1):
                        self.removeCallFromQueue (self._queue_list[i]['id'], STATION_CONNECTED)
                self._queue_list.clear ()
                self._onCallQueueIdle ()
                return
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'clearCallQueue', ex))
    # QUEUE REMOVE CALL from queue
        def removeCallFromQueue (self, call_id: int, event_code: int):
            try:
                call: ipecsAPI.ipecsCalls.ipecsCall
                rec: dict = {}
                if len (self._queue_list) > 0:
                    # Check if call_id is in queue list
                    q_obj = self.findQueueObject (call_id)
                    if q_obj is not None:
                        now = datetime.now()
                        # calculate time in queue
                        delta = round ((now - q_obj['times']['ring_start']).total_seconds(), 0)
                        self._queue_time += delta
                        call = self.find (call_id)
                        if call is not None:
                            call.q_ring_time = delta
                            if q_obj['times']['ring_start'] is not None:
                                call.setCallStartTime (q_obj['times']['ring_start'])
                            if call.callStatus == CALL_IS_ACTIVE or event_code == STATION_CONNECTED: #XXX
                                self._onRemoveCallFromQueue (abandoned=False, call_id=call_id)
                                return
                            else:
                                call.call_status = CALL_IS_ABANDONED
                                self._onRemoveCallFromQueue (abandoned=True, call_id=call_id)
                        else:
                            rec = self._missed_call_dict.copy()
                            rec['time-of-call'] = q_obj['times']['ring_start']
                            rec['callRefID']    = call_id
                            rec['source']       = 'Queue'
                            trd = Thread (target=self._mongo.logMissedCall, args=(rec, ) )
                            trd.start ()
                        # Remove the call from queue
                        self._queue_list.remove (q_obj)
                    else:
                        return
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'removeCallFromQueue', ex))
            finally:
                if call is not None:
                    del call
                if rec is not None:
                    del rec
    # QUEUE ADD CALLER INFO TO QUEUE OBJECT
        def addCallerIDToQueue (self, call_id: int, caller_id: str) -> None:
            q_obj = self.findQueueObject (call_id=call_id)
            if q_obj is not None:
                q_obj['callerID'] = caller_id
                return q_obj
            return None
    # QUEUE FIND Q OBJECT
        def findQueueObject (self, call_id: int) -> dict:
            try:
                for q_obj in self._queue_list:
                    if q_obj['id'] == call_id:
                        return q_obj
                return None
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'findQueueObject', ex))
    # APPEND CALL to the list
        def append (self, station, call_id, event=None, in_queue=None, call_dir=None, did=None):
            """Appends a new call object to the list of call objects.
            Should the call object already exist, the function will automatically update the existing record

            Args:
                station ([str] or [int]): The number of the station associated with the call object
                call_id ([str] or [int]): The ID of the associated iPECs call events
                event ([int], optional): event-code of the actual event that triggered this call. Defaults to None.
                in_queue ([bool], optional): Defines whether the call is currently in the queue [True]. Defaults to None.
                call_dir ([bool], optional): Defines the call direction - DIR_INBOUND for inbound, DIR_OUTBOUND for outbund . Defaults to None.
            """
            try:
                if isinstance (station, str):
                    _station = int (station)
                else:
                    _station = station
                if isinstance (call_id, str):
                    _call_id = int (call_id)
                else:
                    _call_id = call_id
                call = self.find (call_id=call_id)
                if call is None:
                    call = ipecsAPI.ipecsCalls.ipecsCall (
                        call_id=_call_id, 
                        call_summary=self._call_summary_dict, 
                        station=_station, 
                        event=event, 
                        did=did, 
                        oncallclosed=self._onCallClosed, 
                        oncallconnected=self._onCallConnected, 
                        oncallabandoned=self._onCallAbandoned, 
                        oncallupdate=self._onCallUpdate, 
                        onOutboundCall=self._onOutboundCall)
                    self._calls.append (call)
                    return call
                else:
                    self.update (call_id=call_id, station=station, event=event, in_queue=in_queue, call_dir=call_dir, did=did)
                self._log.debug (resources['calls']['c012'].format (station, call_id))
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'append', ex))
    # CLEAR CALLS -> clear one or all call records
        def clear (self, call_id=None, station=None) -> None:
            """Clears/Deletes either a single call object from the object list or clears the whole list, if no parameter is specified.

            Args:
                call_id ([str] or [int], optional): The call reference number to be deleted. Defaults to None.
                station ([str] or [int], optional): The station ID to be deleted. Defaults to None.
            """
            try:
                if isinstance (station, str):
                    _station = station
                else:
                    _station = str (station)
                if isinstance (call_id, str):
                    _call_id = int (call_id)
                else:
                    _call_id = call_id
                for call in self._calls:
                    if _station is None and _call_id is not None:
                        self._log.debug (resources['calls']['c013'].format (station, call_id))
                        if call.call_ID == _call_id:
                            self._upd_hist_func (call)
                            self._calls.remove (call)
                            return
                    elif _station is not None and _call_id is None:
                        if call.station_ID == _station:
                            self._upd_hist_func (call)
                            self._calls.remove(call)
                            return
                    elif _station is not None and _call_id is not None:
                        if call.station_ID == _station and call.call_ID == _call_id:
                            self._upd_hist_func (call)
                            self._calls.remove(call)
                            return
                if _station is None and _call_id is None:
                    for call in self._calls:
                        self._upd_hist_func (call)
                    self._calls.clear()
                    self._log.debug (resources['calls']['c014'])
                return
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'clear', ex))
    # FIND CALL -> find a specific station or call record
        def find (self, call_id=None, station=None) -> object:
            """Searches for a call object specified by the parameters.

            Args:
                call_id ([str] or [int], optional): The call reference number to be searched. Defaults to None.
                station ([str] or [int], optional): The station ID to be searched. Defaults to None.

            Returns:
                object: The call object if found, None if the object is not found.
            """
            try:
                # Force station and call ID to int type 
                for call in self._calls:
                    if call_id is not None and station is None:
                        if call.call_ID == int (call_id):
                            return call
                    elif call_id is None and station is not None:
                        if call.station_ID == int (station):
                            return call
                    elif station is not None and call_id is not None:
                        if call.station_ID == int (station) and call.call_ID == int (call_id):
                            return call
                    else:
                        continue
                return None
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'find', ex))
    # UPDATE CALL Record 
        def update (self, call_id, station=None, event=None, in_queue=None, call_dir=None, did=None):
            """Updates an existing call object in the list of call objects.
            Should the call object not yet exist, the function will automatically create a new record

            Args:
                station ([str] or [int]): The number of the station associated with the call object
                call_id ([str] or [int]): The ID of the associated iPECs call events
                event ([int], optional): event-code of the actual event that triggered this call. Defaults to None.
                in_queue ([bool], optional): Defines whether the call is currently in the queue [True]. Defaults to None.
                call_dir ([bool], optional): Defines the call direction - INBOUND for inbound, DIR_OUTBOUND for outbund . Defaults to None.
            """
            # Force station and call ID to int type 
            try:
                if isinstance (station, str):
                    _station = int (station)
                else:
                    _station = station
                if isinstance (call_id, str):
                    _call_id = int (call_id)
                else:
                    _call_id = call_id

                call = self.find (call_id=_call_id, station=_station)
                # Record found - update data
                if call is not None:
                    call.call_ID = call_id
                    call.station_ID = station
                    if in_queue is not None:
                        call.inQueue = in_queue
                    if call_dir is not None:
                        call.call_Direction = call_dir
                    if did is not None:
                        if event == CALLER_INF_INCOMING or event == DID_INFO_INCOMING or event == OUTBOUND_CALL:
                            call.phone_Number = did
                    # This has to be the last statement in this sequence
                    if event is not None:
                        # Setting this value will trigger the processing of the event
                        call.call_Event = event
                    self._log.debug (resources['calls']['c015'].format (_station, _call_id))
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'update', ex))
    # CALLS LIST GET -> return list of registered call reference numbers
        def call_list (self) -> list:
            """Returns a list of all registered call reference numbers 

            Returns:
                list: list of call reference numbers [int. int, int, ...] or None if no call reference numbers are found
            """
            lst = []
            if len(self._calls) > 0:
                for call in self._calls:
                    lst.append (call.call_ID)
                return lst
            else:
                return None
    # CALL SUMMARY -> return the summary of a single call
        def callSummary (self, call_id, station=None) -> dict:
            call = self.find (call_id, station=station)
            if call is not None:
                return call.call_summary ()
            else:
                return None
    # STATION CALLS SUMMARY -> compile a summary of all calls handled by a specified station/agent
        def summaryOfCallsByStation  (self, station, agt_summary: dict) -> dict:
            try:
                # Force station and call ID to int type 
                if isinstance (station, str):
                    _station = int (station)
                elif isinstance (station, int):
                    _station = station
                ss = agt_summary
                try:
                    if self.find (_station) is not None:
                        ss['station'] = _station
                        for call in self._calls:
                            if call.station_ID == _station:
                                if call.call_Direction:
                                    ss['answered-calls'] += 1
                                else:
                                    ss['outbound-calls'] += 1
                                ss['total-handle-time']  += call.handle_time
                                ss['total-hold-time']    += call.hold_time
                                ss['total-ring-time']    += call.ring_time
                                ss['total-talk-time']    += call.talk_time
                            else:
                                continue
                    return ss
                finally:
                    del ss
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'stationCallSummary', ex))
    # Stations List -> return list of registered stations
        def station_list (self) -> list:
            """Returns a list of all registered stations 

            Returns:
                list: list of stations [int. int, int, ...] or None if no stations are found
            """
            if len (self._calls) > 0:
                lst = []
                for call in self._calls:
                    lst.append (call.station_ID)
                return lst
            else:
                return None
    # Stations Remove Calls -> remove all call records from a specified station / agent
        def removeCalls (self, station) -> None:
            try:
                # Force station and call ID to int type 
                if isinstance (station, str):
                    _station = int (station)
                elif isinstance (station, int):
                    _station = station
                for call in self._calls:
                    # Delete call, but only if the call is not in a state that is still active
                    if call.station_ID == _station and (call.callStatus == CALL_IS_ABANDONED or call.callStatus == CALL_IS_CLOSED):
                        self._upd_hist_func (call)
                        self._calls.remove (call)
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'removeCalls', ex))
    # Reset at end of period -> when the contact center has to go back to 0
        def resetCounters (self, stations: dict) -> None:
            try:
                # First we need to get the individual call history for each station
                if stations is not None:
                    for stn in stations:
                        # get the summary information and write the summary information to database
                        try:
                            agt_summary = self.summaryOfCallsByStation (station=stn, agt_summary=self._agt_summary_dict)
                            if agt_summary is not None:
                                agt_summary['total-wrap-time'] = self._get_wrp_tm_func (stn)
                            # asyncio.ensure_future (self._mongo.logAgentSummary (pay_load=agt_summary))
                            trd = Thread (target=self._mongo.logAgentSummary, args=(agt_summary, ) )
                            trd.start()
                        except:
                            pass
                    # Once done, clear calls list
                    for call in self._calls:
                        if not call.is_active:
                            self._calls.remove (call)
                # Reset all counters, omitting those that might still be active at time of reset,
                # such as: calls_in_queue, calls_onhold, calls_active, calls_in_wrap
                self._calls_abandoned   = 0
                self._calls_answered    = 0
                self._calls_inbound     = 0
                self._calls_outbound    = 0
                self._total_talk_time   = 0.0
                self._total_hold_time   = 0.0
                self._total_out_time    = 0.0
                self._total_ring_time   = 0.0
                self._total_wrap_time   = 0.0
                self._total_handle_time = 0.0
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'resetCounters', ex))
    # Definition of properties
        def getCallStats (self) -> dict:
            try:
                avgTLK: float = 0.0
                avgHLD: float = 0.0
                avgHDL: float = 0.0
                avgABD: float = 0.0
                avgRNG: float = 0.0
                if self._calls_answered > 0:
                    avgTLK = round (self._total_talk_time / self._calls_answered, 0)
                    avgHLD = round (self._total_hold_time / self._calls_answered, 0)
                    avgHDL = round ((self._total_talk_time + self._total_wrap_time) / self._calls_answered, 0)
                    avgRNG = round (self.total_ring_time / self._calls_answered, 0)
                if self._calls_inbound > 0:
                    avgABD = round (self._calls_abandoned / self._calls_inbound, 2)

                totals = {
                    "Calls": {
                        "Inbound":      self._calls_inbound, 
                        "Outbound":     self._calls_outbound, 
                        "Answered":     self._calls_answered,
                        "Abandoned":    self._calls_abandoned,
                    },
                    "Times": {
                        "Talk":     self._total_talk_time,
                        "Hold":     self._total_hold_time,
                        "Out":      self._total_out_time,
                        "Ring":     self._total_ring_time,
                        "Handle":   self._total_talk_time + self._total_wrap_time 
                    },
                    "Averages": {
                        "avgTalk":      avgTLK,
                        "avgHold":      avgHLD,
                        "avgHandle":    avgHDL,
                        "AbandonRate":  avgABD,
                        "ASA":          avgRNG
                    }
                }
                return totals
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, 'getCallStats', ex))
    # -------------------------------------------------------------------------------------------------
    #   CALLS CLASS PROPERTIES AND METHODS
    # -------------------------------------------------------------------------------------------------
        @property
        def calls_abandoned (self) -> int:
            return self._calls_abandoned
        @property
        def calls_active (self) -> int:
            return self._calls_active
        @property
        def calls_answered (self) -> int:
            return self._calls_answered
        @property
        def calls_in_queue (self) -> int:
            return self._calls_in_queue
        @property
        def calls_on_hold (self) -> int:
            return self._calls_on_hold
        @property
        def calls_ringing (self) -> int:
            return self._calls_ringing
        @property
        def calls_inbound (self) -> int:
            return self._calls_inbound
        @property
        def calls_outbound (self) -> int:
            return self._calls_outbound
        @property
        def total_talk_time (self) -> float:
            return self._total_talk_time
        @property
        def total_hold_time (self) -> float:
            return self._total_hold_time
        @property
        def total_out_time (self) -> float:
            return self._total_out_time
        @property
        def total_ring_time (self) -> float:
            return self._total_ring_time
        @property
        def total_handle_time (self) -> float:
            return self._total_handle_time     
        def setOnCallAnswered_Func (self, function: object) -> None:
            self._oncall_ans_func = function  
        def setOnCallClosed_Func (self, function: object) -> None:
            self._oncall_closed_func = function
    # -------------------------------------------------------------------------------------------------
    #   CALLS CLASS CALLBACK FUNCTIONS
    # -------------------------------------------------------------------------------------------------
        def _onCallAbandoned (self, call_id, summary):
            try:
                rec:dict = {}
                call = self.find (call_id)
                if call is not None:
                    call.callStatus = CALL_IS_ABANDONED
                    if self._calls_in_queue > 0:
                        self._calls_in_queue -= 1
                    self._calls_abandoned += 1
                if summary is not None:
                    self._total_ring_time += summary['ring-time']
                    # trd = Thread (target=self._mongo.logCallHistory, kwargs=dict(pay_load=summary, ))
                    #trd = ipecs_db_io.threadLogCallHistory (pay_load=summary)
                    trd = Thread (target=self._mongo.logCallHistory, args=(summary, ) )
                    trd.start()
                    rec = self._updateAbandonedCallRecord (summary=summary)
                    if rec is not None:
                        trd = Thread (target=self._mongo.logMissedCall, args=(rec, ) )
                        trd.start()
                    self.clear (call_id)
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallAbandoned', ex))
            finally:
                self._callback_func ()
                if call is not None:
                    del call
                if rec is not None:
                    del rec
        def _onCallConnected (self, call_id: int, station_id: int):
            try:
                # Remove this call from the call queue
                if self.findQueueObject (call_id) is not None:
                    self.removeCallFromQueue (call_id=call_id, event_code=STATION_CONNECTED) 
                if ((self._calls_answered) < (self._calls_inbound - self._calls_abandoned)):
                    self._calls_answered += 1
                self._calls_active   += 1
                if self._calls_in_queue > 0:                                                             
                    self._calls_in_queue -= 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallConnected', ex))
            finally:
                if self._oncall_ans_func is not None:
                    self._oncall_ans_func (station_id)
                self._callback_func ()
        def _onCallClosed (self, summary: dict):
            try:
                if self._calls_active > 0:
                    self._calls_active  -= 1
                if summary is not None:
                    self._total_talk_time   += summary['talk-time']
                    self._total_hold_time   += summary['hold-time']
                    if summary['direction'] == DIR_OUTBOUND:
                        self._total_out_time += summary['talk-time']
                    self._total_ring_time   += summary['ring-time']
                    self._total_handle_time += (summary['talk-time'] + summary['hold-time'])
                    # trd = Thread (target=self._mongo.logCallHistory, kwargs=dict(pay_load=summary, ))
                    trd = Thread (target=self._mongo.logCallHistory, args=(summary, ) )
                    trd.start ()
                    self.clear (call_id=summary['callRefID'])
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallClosed', ex))
            finally:
                if self._oncall_closed_func is not None and summary['stationID'] is not None:
                    self._oncall_closed_func (int (summary['stationID']))
                self._callback_func ()
        def _onOutboundCall (self, call) -> None:
            try:
                self._calls_outbound += 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onOutboundCall', ex))
            finally:
                self._callback_func ()
        def _onCallInQueue (self):
            try:
                self._calls_in_queue += 1
                self._calls_inbound  += 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallInQueue', ex))
            finally:
                self._callback_func ()
        def _onCallQueueIdle (self) -> None:
            try:
                self._calls_in_queue = 0
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallQueueIdle', ex))
            finally:
                self._callback_func ()
        def _onRemoveCallFromQueue (self, abandoned: bool=False, call_id: int=None):
            try:
                if self._calls_in_queue > 0:
                    self._calls_in_queue -= 1
                if abandoned:
                    call = self.find (call_id)
                    if call is not None:
                        if call.station_ID in queues_allowed:
                            self._calls_abandoned += 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onRemoveCallFromQueue', ex))
            finally:
                self._callback_func ()
        def _onCallUpdate (self):
            try:
                self._calls_in_wrap = 0
                self._calls_on_hold = 0
                for call in self._calls:
                    if call.call_status == CALL_IS_IN_WRAP:
                        self._calls_in_wrap += 1
                    if call.call_status == CALL_IS_ONHOLD:
                        self._calls_on_hold += 1
                    if call.call_status == CALL_IS_RINGING:
                        self._calls_ringing += 1
            except Exception as ex:
                self._log.error (resources['err']['errgen'].format(self.__class__, '_onCallUpdate', ex))
            finally:
                self._callback_func ()
        def _updateAbandonedCallRecord (self, summary: dict) -> dict:
            if summary is not None:
                rec:dict = {}
                try:
                    rec = self._missed_call_dict.copy()
                    rec['time-of-call'] = summary['start-time']
                    rec['stationID']    = summary['stationID']
                    rec['callRefID']    = summary['callRefID']
                    rec['callerID']     = summary['callerID']
                    rec['source']       = 'Station'
                    return rec
                except Exception as ex:
                    self._log.error (resources['err']['errgen'].format(self.__class__, '_updateAbandonedCallRecord', ex))
                finally:
                    if rec is not None:
                        del rec
# ==================================================================================================
#   CALL CLASS DEFINITION
#       SUPPORTS THE FOLLOWING EVENT CODES: 3, 2, 43, 44, 49, 50, 57, 62, 66, 67 
#       QUEUE_INCOMING_CALL, STATION_RINGING, STATION_CONNECTED, STATION_ANSWERED, STATION_ON_HOLD, 
#       ACD_ON_HOLD, STATION_OFF_HOLD, STATION_OFF_HOLD, STATION_ABANDONED, STATION_DISCONNECTED, 
#       OUTBOUND_CALL
# ==================================================================================================
        class ipecsCall ():
            _stationID:     int
            _call_id:       int
            _event:         int
            _prev_event:    int
            _call_status:   int
            _is_in_queue:   bool
            _is_active:     bool
            _notify_sent:   bool
            _call_dir:      bool
            _time_format:   str
            _did:           str
            _call_summary:  dict
        # Declaration of Time related variables
            _log:               logging.Logger
            _ts_active_start:   datetime
            _ts_hold_start:     datetime
            _ts_out_start:      datetime
            _ts_ring_start:     datetime
            _ts_active_end:     datetime
            _ts_out_end:        datetime
            _ts_hold_end:       datetime
            _ts_ring_end:       datetime
            _total_talk_time:   float
            _total_hold_time:   float
            _total_out_time:    float
            _total_ring_time:   float
            _total_q_ring_time: float
            _total_queue_time:  float
            _total_wrap_time:   float
            _total_handle_time: float
        # declaration of Callback Functions
            _onCallClosed:      object
            _onCallConnected:   object
            _onCallAbandoned:   object
            _onCallUpdate:      object
            _onCallInQueue:     object
            _onOutboundCall:    object
        # Class initialisation
            def __init__ (self, call_id: int, call_summary:dict, station:int=0, event=None, in_queue=None, call_dir=None, time_format='%Y/%m/%d %H:%M:%S%f', did=None, 
                          oncallclosed=None, oncallconnected=None, oncallabandoned=None, oncallupdate=None, onOutboundCall=None) -> None:
                """Initialises the call class

                Args:
                    station ([str] or [int]): The number of the station associated with the call object
                    call_id ([str] or [int]): The ID of the associated iPECs call events
                    event ([int], optional): event-code of the actual event that triggered this call. Defaults to None.
                    in_queue ([bool], optional): Defines whether the call is currently in the queue [True]. Defaults to None.
                    call_dir ([bool], optional): Defines the call direction - DIR_INBOUND for inbound, DIR_OUTBOUND for outbund . Defaults to None.
                    time_format ([str]), optional): The formatting string for datetime operations. Defaults to '%Y/%m/%d %H:%M:%S%f'.
                """
                self._log               = logging.getLogger(LOGGING_ID)
                self._onCallClosed      = oncallclosed
                self._onCallConnected   = oncallconnected
                self._onCallAbandoned   = oncallabandoned
                self._onCallUpdate      = oncallupdate
                self._onOutboundCall    = onOutboundCall
                self._time_format       = time_format
                self._call_summary      = call_summary
                self._call_status       = CALL_IS_UNDEFINED
                self._call_id           = 0
                self._station_id        = 0
                self._event             = 0
                self._prev_event        = 0
                self._is_in_queue       = False
                self._notify_sent       = False
                self._ts_active_start   = None
                self._ts_hold_start     = None
                self._ts_ring_start     = None
                self._ts_out_start      = None
                self._ts_active_end     = None
                self._ts_out_end        = None
                self._ts_hold_end       = None
                self._ts_ring_end       = None
                self._did               = ''
                self._total_talk_time   = 0.0
                self._total_hold_time   = 0.0
                self._total_out_time    = 0.0
                self._total_ring_time   = 0.0
                self._total_q_ring_time = 0.0
                self._total_handle_time = 0.0
            # Assignment
                try:
                    self._call_summary = call_summary
                    self._is_active = True
                    if call_id is not None:
                        self._call_id = call_id
                    if station is not None:
                        if isinstance (station, str):
                            self._station_id = int (station)
                        if isinstance (station, int):
                            self._station_id = station
                    if call_dir is not None:
                        self._call_dir = call_dir
                    else:    
                        self._call_dir = DIR_INBOUND
                    if did is not None:
                        self._did = did
                    if event is not None:
                        self._event = event
                    if event == QUEUE_INCOMING_CALL:
                        self._is_in_queue = True
                        self._call_status = CALL_IS_IN_QUEUE
                    elif in_queue is not None:
                        self._is_in_queue = in_queue
                        if in_queue:
                            self._is_in_queue = True
                            self._call_status = CALL_IS_IN_QUEUE
                    self._parse_event ()
                    return
                except Exception as ex:
                    self._log.error (resources['err']['errgen'].format(self.__class__, '__init__', ex))
            def __str__ (self) -> str:
                return (f'Call ID: {self._call_id}, Station ID: {self._stationID}, Last Event: {self._event}, Queued: {self._is_in_queue}, Direction: {self._call_dir}')
            def __del__ (self) -> None:
                pass
        # -------------------------------------------------------------------------------------------------
        # CALL EVENT PARSER
        # -------------------------------------------------------------------------------------------------
            def _parse_event (self, did=None) -> None:
                try:
                    # No change in event ignore and return
                    if self._prev_event == self._event:
                        return
                    now = datetime.now()
                # The queue is ringing due to incoming call (Code 3)
                    if self._event == STATION_RINGING or self._event == CALLER_INF_INCOMING or self._event == DID_INFO_INCOMING:
                        if self._ts_ring_start is None:
                            self._ts_ring_start = now
                            self._call_status   = CALL_IS_RINGING
                            self._is_in_queue = False
                        return
                    # Was the Station Ringing before?
                    elif self._prev_event == STATION_RINGING:
                        # Is the new event IDLE? -> Then we can assume the caller hung up
                        if self._event == STATION_IDLE or self._event == STATION_DISCONNECTED:
                            self._call_status = CALL_IS_ABANDONED
                            if self._ts_ring_start is not None and isinstance (self._ts_ring_start, datetime):
                                self._total_ring_time = round ((now - self._ts_ring_start).total_seconds(), 0)
                            self._onCallAbandoned (self._call_id) 
                # Agent started outbound call
                    elif self._event == OUTBOUND_CALL:
                        self._ts_out_start    = now
                        self._ts_active_start = now
                        self._call_dir        = DIR_OUTBOUND
                        self._call_status     = CALL_IS_ACTIVE
                        if did is not None:
                            self._did = did
                        else:
                            self._did = 'unknown number'
                        self._onOutboundCall ()
                        return
                # Call has been answered
                    elif self._event == STATION_CONNECTED or self._event == STATION_ANSWERED or self._event == STATION_SEIZED:
                        self._ts_ring_end = datetime.now()
                        if self._ts_ring_start is not None and isinstance (self._ts_ring_start, datetime):
                            self._total_ring_time = round ((now - self._ts_ring_start).total_seconds(), 0)
                        self._ts_active_start = now
                        #if self._event == STATION_SEIZED:
                        self._call_status = CALL_IS_ACTIVE
                        self._onCallConnected (self._call_id, self._station_id)
                        return
                # Agent goes on hold - this can happen several times during a call, so need to keep taps
                    elif self._event == STATION_ON_HOLD or self._event == ACD_ON_HOLD:
                        self._ts_hold_start = now
                        self._call_status   = CALL_IS_ONHOLD
                        self._onCallUpdate ()
                        return
                # Call disconnected for 1 of 3 reasons
                    elif self._event == STATION_OFF_HOLD and self._call_status == CALL_IS_ONHOLD:
                        if self._ts_hold_start is not None and isinstance (self._ts_hold_start, datetime):
                            self._total_hold_time += round ((now - self._ts_hold_start).total_seconds(), 0)
                        self._call_status = CALL_IS_ACTIVE
                        self._onCallUpdate ()
                        return
                    elif  self._event == STATION_ABANDONED or self._event == STATION_DISCONNECTED:
                        # This call is not active anymore
                        self._is_active = False
                        if self._event != STATION_ABANDONED and self._call_status != CALL_IS_ABANDONED:
                            if self._ts_out_start is not None and isinstance (self._ts_out_start, datetime) and self._call_dir == DIR_OUTBOUND:
                                self._total_out_time = round ((now - self._ts_out_start).total_seconds(), 0)
                            if self._ts_active_start is not None and isinstance (self._ts_active_start, datetime):
                                self._total_talk_time   = round ((now - self._ts_active_start).total_seconds() - self._total_ring_time - self._total_hold_time, 0)
                            self._total_handle_time = round ((now - self._ts_active_start).total_seconds(), 0)
                        if self._event == STATION_ABANDONED or self._call_status == CALL_IS_ABANDONED:
                            if self._ts_ring_start is not None and isinstance (self._ts_ring_start, datetime):
                                self._total_ring_time   = round ((now - self._ts_ring_start).total_seconds(), 0)
                            self._onCallAbandoned (call_id=self._call_id, summary=self.call_closed_summary())
                            return
                        if self._event == STATION_DISCONNECTED or self._call_status == QUEUE_IDLE:
                            self._call_status = CALL_IS_CLOSED
                            self._onCallClosed (summary=self.call_closed_summary())
                            return
                except Exception as ex:
                    self._log.error (resources['err']['errgen'].format(self.__class__, '_parse_event', ex))
                finally:
                    self._prev_event = self._event
            #TODO: need to implement disconnect cause - later
        # -------------------------------------------------------------------------------------------------
        # CALL CLOSED SUMMARY
        # -------------------------------------------------------------------------------------------------
            def call_closed_summary (self) -> dict:
                cs = {}
                stat_msg = ''
                dir_msg  = 'inbound'
                try:
                    if self._call_status == CALL_IS_UNDEFINED:
                        stat_msg = 'undefined'
                    elif self._call_status == CALL_IS_RINGING:
                        stat_msg = 'ringing'
                    elif self._call_status == CALL_IS_ONHOLD:
                        stat_msg = 'on hold'
                    elif self._call_status == CALL_IS_ACTIVE:
                        stat_msg = 'active'
                    elif self._call_status == CALL_IS_IN_WRAP:
                        stat_msg = 'in wrap'
                    elif self._call_status == CALL_IS_CLOSED:
                        stat_msg = 'closed'
                    elif self._call_status == CALL_IS_ABANDONED:
                        stat_msg = 'abandoned'
                    else:
                        stat_msg = 'N/A'
                    if self._call_dir != DIR_INBOUND:
                        dir_msg = 'outbound'
                # Load call summary template
                    cs = self._call_summary
                # Populate values
                    cs['callRefID']   = self._call_id
                    cs['stationID']   = self._station_id
                    cs['callerID']     = self._did
                    cs['call-type']   = dir_msg
                    cs['call-status'] = stat_msg
                    if self._call_status == CALL_IS_ABANDONED:
                        cs['start-time'] = self._ts_ring_start
                    else:
                        cs['start-time']  = self._ts_active_start
                    cs['end-time']    = datetime.now()
                    cs['ring-time']   = self._total_ring_time
                    cs['direction']   = self._call_dir
                    cs['talk-time']   = self._total_talk_time
                    cs['hold-time']   = self._total_hold_time
                    cs['queue-time']  = self._total_q_ring_time
                    if self._call_dir == DIR_OUTBOUND:
                        cs['talk-time'] = self._total_out_time
                    return cs
                    # return {"callRef": self._call_id, "status": stat_msg, "direction": dir_msg, "phoneNo": self._did, "ringTime": self.ring_time, "queueTime": self.queue_time, "holdTime": self.hold_time, "talkTime": self.talk_time, "handleTime": self.handle_time}
                except Exception as ex:
                    self._log.error (resources['err']['errgen'].format(self.__class__, 'call_closed_summary', ex))
                finally:
                    del stat_msg
                    del dir_msg
                    del cs
#-------------------------------------------------------------------------------------------------
#   CALL CLASS PROPERTIES AND METHODS
# -------------------------------------------------------------------------------------------------

        # General properties
            def setCallStartTime (self, value: datetime) -> None:
                self._ts_active_start = value 
            @property
            def Call_To_Dict (self) -> dict:
                return {"Call_ID": self._call_id, "Station_ID": self._station_id, "Last_Event": self._event, "Is_In_Queue": self._is_in_queue, "Call_Direction": self._call_dir}
            @property
            def station_ID (self) -> int:
                return self._station_id
            @station_ID.setter
            def station_ID (self, value) -> None:
                self._station_id = value
            @property
            def call_ID (self) -> int:
                return self._call_id
            @call_ID.setter
            def call_ID (self, value) -> None:
                self._call_id = value
            @property
            def call_Event (self) -> int:
                return self._event
            @call_Event.setter
            def call_Event (self, event) -> None:
                # Call is already in this state, ignore
                if self._prev_event == event:
                    return
                self._prev_event = self._event
                self._event      = event
                # Maintain sequence, as parse event uses the self._event stored variable
                self._parse_event ()
            @property
            def callStatus (self) -> int:
                return self._call_status
            @callStatus.setter
            def callStatus (self, value) -> None:
                self._call_status = value
            @property
            def is_active (self) -> bool:
                return self._is_active
            @property
            def inQueue (self) -> bool:
                return self._is_in_queue
            @inQueue.setter
            def inQueue (self, value) -> None:
                self._is_in_queue = value
            @property
            def notification_sent (self) -> bool:
                return self._notify_sent
            @notification_sent.setter
            def notification_sent (self, value: bool) -> None:
                self._notify_sent = value
            @property
            def call_Direction (self) -> bool:
                return self._call_dir
            @call_Direction.setter
            def call_Direction (self, direction=DIR_INBOUND) -> None:
                self._call_dir = direction
            @property
            def phone_Number (self) -> str:
                return self._did
            @phone_Number.setter
            def phone_Number (self, value) -> None:
                self._did = value
        # Properties for Time Values    
            @property 
            def talk_time (self) -> float:
                return self._total_talk_time
                #try:
                #    if self._ts_active_start is not None and isinstance (self._ts_active_start, datetime) and self._ts_active_end is not None and isinstance (self._ts_active_end, datetime):
                #        return round ((self._ts_active_end - self._ts_active_start).total_seconds(), 0) #XXX
                #    else:
                #        return 0.0
                #except Exception as ex:
                #    self._log.error (resources['err']['errgen'].format(self.__class__, '@property:talk_time', ex))
            @property
            def ring_time (self) -> float:
                return self._total_ring_time
            @ring_time.setter
            def ring_time (self, value: float):
                self._total_ring_time = value
            @property
            def q_ring_time (self) -> float:
                return self._total_q_ring_time
            @q_ring_time.setter
            def q_ring_time (self, value: float) -> None:
                self._total_q_ring_time = value
            @property 
            def hold_time (self):
                return self._total_hold_time
            @property
            def call_status (self) -> int:
                return self._call_status
            @call_status.setter
            def call_status (self, value: int) -> None:
                self._call_status = value
            @property
            def handle_time (self):
                return self._total_handle_time

# -------------------------------------------------------------------------------------------------
#                   DEFINITION FOR CUSTOM EXCEPTIONS
# -------------------------------------------------------------------------------------------------
    class exceptions ():
        class ServerUnreachable (Exception):
            """Exception raised when login attempts exceeded

            Attributes (args) in order:
                message -- explanation of the error
            """
            def __init__(self, *args):
                if args:
                    self.message = args[0]
                else:
                    self.message = "The iPECs server to connect to is unreachable!"

                super().__init__(self.message)
        class LoginRetryAttemptsExceeded (Exception):
            """Exception raised when login attempts exceeded

            Attributes (args) in order:
                message -- explanation of the error
            """
            def __init__(self, *args):
                if args:
                    self.message = args[0]
                else:
                    self.message = "Number of login attempts exceeded retry-attempts value!"

                super().__init__(self.message)
        class ConnectionClosed (Exception):
            """Exception raised when socket connection closes unexpectedly

            Attributes (args) in order:
                message -- explanation of the error
            """
            def __init__(self, *args):
                if args:
                    self.message = args[0]
                else:
                    self.message = "Connection closed unexpectedly!"

                super().__init__(self.message)
        class ConnectionRefused (Exception):
            """Exception raised when socket connection refused by server

            Attributes (args) in order:
                message -- explanation of the error
            """
            def __init__(self, *args):
                if args:
                    self.message = args[0]
                    if len (args) > 1:
                        self.status_code = args[1]
                    else:
                        self.status_code = -1
                else:
                    self.message = "Server refused connection."

                super().__init__(self.message, self.status_code)
        class NotConnected (Exception):
            """Exception raised when socket connection refused for an unknown reason

            Attributes (args) in order:
                message -- explanation of the error
            """
            def __init__(self, *args):
                if args:
                    self.message = args[0]
                    if len (args) > 1:
                        self.status_code = args[1]
                    else:
                        self.status_code = -1
                else:
                    self.message = "Could not establish socket connection."

                super().__init__(self.message, self.status_code)
        class UnknownEventFormat (Exception):
            """Exception raised when socket returns an event that does not meet standard template

            Attributes (args) in order:
                message -- explanation of the error
            """
            def __init__(self, *args):
                if args:
                    self.message = args[0]
                else:
                    self.message = "Server returned unknown event format."

                super().__init__(self.message)
        class MongoConnectionClosed (Exception):
            """Exception raised when connection to mongo database is closed unexpectedly

            Attributes (args) in order:
                message -- detailled explanation of the error
            """
            def __init__(self, *args):
                if args:
                    self.message = args[0]
                else:
                    self.message = "Connection to Mongo Database closed."

                super().__init__(self.message)
