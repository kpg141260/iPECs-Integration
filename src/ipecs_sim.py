import os
import logging
import json
import time

from logging        import Logger
from ipecsAPI       import ipecsAPI
from ipecs_config   import ipecs_config
from ipecs_mongo    import ipecs_db_io
from datetime       import datetime

# iPECs Event Definitions
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

class ipecsSim ():
    _log:       Logger
    __cb_func:  object
    _mongo:     ipecs_db_io 
    _ipecs:     ipecsAPI
    _sim_cmds:  dict
    _call_id:   int
    _ts_format: str
    _sim_file:  str
    _is_initialised: bool = False

# Class INIT
    def __init__ (self, sim_file: str, call_id: int, mongo: ipecs_db_io, config: ipecs_config, ipecs: ipecsAPI, cb_func: object):
        self._log       = logging.getLogger ('iPECsSimulator')
        self._cb_func   = cb_func
        self._sim_file  = sim_file
        self._mongo     = mongo
        self._cnf       = config
        self._ipecs     = ipecs
        self._call_id   = call_id
        self._sim_cmds  = {}
        self._ts_format = self._cnf.ipecs_event_date_format
        self._load_parameters ()
# Calls DEL
    def __del__ (self) -> None:
        try:
            self._cb_func ()
            self._log.info (self._cnf.getResourceString('inf', 'inf013').format("iPECs Simulator module"))
            del self._ts_format
            del self._sim_cmds
            del self._call_id
            del self._sim_file
        except Exception as ex:
            self._log.error (f'{self.__class__}.__del__ -> {ex}')
    def shutdown (self) -> None:
        self.__del__()
# Load Parameters
    def _load_parameters (self) -> None:
        """Method loads all parameters and commands needed for simulation engine of iPECs API simulator

        Raises:
            PermissionError: Raised if file cannot be accessed due to file permission errors.
            FileNotFoundError: Raised if file cannot be found / does not exist.
        """
        try:
            # Check if resource-file exists
            if not os.path.exists(self._sim_file):
                self._log.error (self._cnf.getResourceString('sim', 'sim001').format(self.__class__, self._sim_file))
            with open (self._sim_file, 'r') as json_file:
                # Parse file data 
                self._sim_cmds = json.loads(json_file.read())
            json_file.close()
            self._is_initialised = True
            del self._sim_file
        except PermissionError as ex:
            self._log.fatal (self._cnf.getResourceString('sim', 'sim002').format(self.__class__, self._sim_file))
        except Exception as ex:
            raise (f'{self.__class__}._load_parameters -> {ex}')

# =======================================================================================
# Simulation Commands
# =======================================================================================
    def _get_time_stamp (self) -> str:
        try:
            return datetime.now().strftime (self._ts_format)
        except Exception as ex:
            self._log.error (self._cnf.getResourceString('sim', 'sim003').format(self.__class__, '_set_time_stamp', ex))
# Station LOGIN
    def station_login (self, stn_id: int) -> None:
        cmd:      dict = {}
        cmds_seq: dict = {}
        try:
            cmds_seq = self._sim_cmds['cmd_sequences']['station_login']
            for key in cmds_seq.keys():
                cmd_key = cmds_seq[key]
                cmd     = self._sim_cmds[cmd_key]
                cmd['data']['time']         = self._get_time_stamp ()
                cmd['data']['sourceNumber'] = str (stn_id)
                # Delay by delay amount specified in simulator cmd structure
                if cmd['delay'] > 0.0:
                    time.sleep (cmd['delay'])
                self._ipecs.simulate_ipecs_command (cmd)
        except Exception as ex:
            self._log.error (self._cnf.getResourceString('err', 'errgen').format(self.__class__, 'make_inbound_call', ex))
# Staion LOGIN
    def station_logout (self, stn_id: int) -> None:
        cmd:      dict = {}
        cmds_seq: dict = {}
        try:
            cmds_seq = self._sim_cmds['cmd_sequences']['station_logout']
            for key in cmds_seq.keys():
                cmd_key = cmds_seq[key]
                cmd     = self._sim_cmds[cmd_key]
                cmd['data']['time']         = self._get_time_stamp ()
                cmd['data']['sourceNumber'] = str (stn_id)
                if cmd['delay'] > 0.0:
                    time.sleep (cmd['delay'])
                self._ipecs.simulate_ipecs_command (cmd)
        except Exception as ex:
            self._log.error (self._cnf.getResourceString('err', 'errgen').format(self.__class__, 'make_inbound_call', ex))
# Agent Login ACD
    def agent_logout (self, stn_id: int) -> None:
        cmd:      dict = {}
        cmds_seq: dict = {}
        try:
            cmds_seq = self._sim_cmds['cmd_sequences']['agent_logout']
            for key in cmds_seq.keys():
                cmd_key = cmds_seq[key]
                cmd     = self._sim_cmds[cmd_key]
                cmd['data']['time']         = self._get_time_stamp ()
                cmd['data']['sourceNumber'] = str (stn_id)
                if cmd['delay'] > 0.0:
                    time.sleep (cmd['delay'])
                self._ipecs.simulate_ipecs_command (cmd)
        except Exception as ex:
            self._log.error (self._cnf.getResourceString('err', 'errgen').format(self.__class__, 'make_inbound_call', ex))
# Agent DND activate and deactivate
    def agent_dnd (self, stn_id: int) -> None:
        cmd:      dict = {}
        cmds_seq: dict = {}
        try:
            cmds_seq = self._sim_cmds['cmd_sequences']['agent_dnd']
            for key in cmds_seq.keys():
                cmd_key = cmds_seq[key]
                cmd     = self._sim_cmds[cmd_key]
                cmd['data']['time']         = self._get_time_stamp ()
                cmd['data']['sourceNumber'] = str (stn_id)
                if cmd['delay'] > 0.0:
                    time.sleep (cmd['delay'])
                self._ipecs.simulate_ipecs_command (cmd)
        except Exception as ex:
            self._log.error (self._cnf.getResourceString('err', 'errgen').format(self.__class__, 'make_inbound_call', ex))
# Agent Unavailable activate and deactivate
    def agent_available (self, stn_id: int) -> None:
        cmd:      dict = {}
        cmds_seq: dict = {}
        try:
            cmds_seq = self._sim_cmds['cmd_sequences']['agent_avail']
            for key in cmds_seq.keys():
                cmd_key = cmds_seq[key]
                cmd     = self._sim_cmds[cmd_key]
                cmd['data']['time']         = self._get_time_stamp ()
                cmd['data']['sourceNumber'] = str (stn_id)
                if cmd['delay'] > 0.0:
                    time.sleep (cmd['delay'])
                self._ipecs.simulate_ipecs_command (cmd)
        except Exception as ex:
            self._log.error (self._cnf.getResourceString('err', 'errgen').format(self.__class__, 'make_inbound_call', ex))
# Simulate an inbound call
    def make_inbound_call (self, call_para:dict) -> None:
        cmd:      dict = {}
        cmds_seq: dict = {}
        try:
            cmds_seq = self._sim_cmds['cmd_sequences']['call_inbound']
            co_idle_cnt = 0
            for key in cmds_seq.keys():
                cmd_key = cmds_seq[key]
                cmd     = self._sim_cmds[cmd_key]
                if cmd['data']['eventCode'] != DELAY_ONLY:
                    cmd['data']['time'] = self._get_time_stamp ()
                    # All events in this sequence have the call reference ID, except for Wrap-up start and Wrap-up end
                    if cmd['data']['eventCode'] != AGENT_ACD_WUP_START and cmd['data']['eventCode'] != AGENT_ACD_WUP_END:
                        cmd['data']['callRefID'] = self._call_id
                        if cmd_key != 'cmd_call_in_queue' or cmd['data']['eventCode'] == STATION_CONNECTED:
                            cmd['data']['destNumber'] = call_para['station']
                        if cmd['data']['eventCode'] == STATION_CONNECTED:
                            cmd['delay'] = call_para['duration']
                    if cmd['data']['eventCode'] == AGENT_ACD_WUP_START or cmd['data']['eventCode'] == AGENT_ACD_WUP_END or cmd['data']['eventCode'] == STATION_IDLE or cmd['data']['eventCode'] == STATION_RINGING or cmd['data']['eventCode'] == STATION_DISCONNECTED:
                        cmd['data']['sourceNumber'] = call_para['station']
                    if cmd['data']['eventCode'] == QUEUE_IDLE:
                        if co_idle_cnt <= 0:
                            cmd['data']['sourceNumber'] = call_para['station']
                            co_idle_cnt += 1
                        else:
                            cmd['data']['sourceNumber'] = "0006"
                            cmd['data']['sourceType'] = "CO" 
                    if cmd_key == 'cmd_call_in_queue_stn':
                        cmd['data']['destNumber'] = call_para['station']
                    # Insert caller id into event if event code is DID_INFO or CALLER_INF
                    if cmd['data']['eventCode'] == DID_INFO_INCOMING or cmd['data']['eventCode'] == CALLER_INF_INCOMING:
                        cmd['data']['data1'] = call_para['caller_id']
                    # Execute command
                    self._ipecs.simulate_ipecs_command (cmd)
                # Delay - simulate activity times
                if cmd['delay'] > 0.0:
                    time.sleep (cmd['delay'])
            # End of for loop
            self._call_id += 1
            self._cb_func (self._call_id)
        except Exception as ex:
            self._log.error (self._cnf.getResourceString('err', 'errgen').format(self.__class__, 'make_inbound_call', ex))

            


