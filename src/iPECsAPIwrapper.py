# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import  os, sys
import  asyncio, subprocess, threading
import  json
import  logging, time
import  configparser

from    __version   import __version__, __product__
from    flask       import Flask
from    flask       import request
from    flask_cors  import CORS
from    ipecsAPI    import ipecsAPI
from    ipecs_sim   import ipecsSim

if sys.version_info < (3, 5):
    print ("Python version must be greater than 3.5 to run iPECs API Wrapper.")
    sys.exit()

app = Flask(__name__)

acdStatus: dict = {
    "stations-connected":   0,
    "stations-idle":        0,
    "stations-busy":        0,
    "agents-logged-in":     0,
    "agents-available":     0,
    "total-calls-in-queue": 0,
    "total-inbound-calls":  0,
    "total-answered-calls": 0,
    "total-abandoned-calls":0,
    "total-outbound-calls": 0,
    "total-calls-onwrap":   0,
    "total-calls-onhold":   0,
    "total-logged-in-time": 0.0,
    "total-avail-time":     0.0,
    "total-unavail-time":   0.0,
    "total-idle-time":      0.0, 
    "total-busy-time":      0.0,
    "total-hold-time":      0.0,
    "total-wrap-time":      0.0,
    "total-ring-time":      0.0,
    "total-talk-time":      0.0,
    "total-handle-time":    0.0,
    "station-list":         []
}
ipecs: ipecsAPI
ipecs_sim: ipecsSim
bool_conStatus: bool  = False
ipecs_api_is_running  = False
last_msg:   str       = ''
conf_file: str        = ''
sim_file: str         = ''
log_id: str           = ''
dict_sim              = {
    "sim_enabled":      False,
    "sim_rec_cnt":      10,
    "sim_exec_dly":     2,
    "sim_call_len":     30,
    "sim_call_len_inc": 3,
    "hold_time":        10
}
err_str_nowrapper: str = "There is no iPECs API Wrapper object."
err_str_post_only: str = "Error -> only POST method is supported for this command.__"

# System information
@app.route('/system/uptime', methods=['GET'])
def iPECsUpTime () -> str:
    return ipecs.get_system_run_time ()
# ACD Related Commands
@app.route ('/system/status', methods=['GET'])
def conStatus () -> dict:
    if not ipecs_api_is_running:
        launch_ipecs_wrapper ()
    return ipecs.getConnectionStatus ()
@app.route('/system/last_msg', methods=['GET'])
def lastSystemMsg () -> dict:
    if not ipecs_api_is_running:
        launch_ipecs_wrapper ()
    return (last_msg)
@app.route('/system/reloadConfig', methods=['GET'])
def reloadConfig () -> None:
    if ipecs is not None:
        try:
            ipecs.loadConfiguration (f_name=os.path.join(os.getcwd(), conf_file), log_id=log_id)
        except Exception as ex:
            return (f'Error loading configuration: {ex}')
        return ("Successfully loaded configuration.") 
@app.route('/system/read_log', methods=['GET', 'POST'])
def readLog () -> object:
    if not ipecs_api_is_running:
        launch_ipecs_wrapper ()
    if request.method == 'GET':
        return ipecs.readLinesFromLogFile (10)
    if request.method == 'POST':
        num_lines: str = request.args.get ('lines')
        if not num_lines.isdigit():
            return f'Invalid Parameter [{num_lines}] in HTTP request -> only positive integer numbers are allowed.'
        lines = int (num_lines)
        if lines > 100: lines = 100
        try:
            log_level = request.args.get('filter')
            if not log_level in ['debug', 'info', 'warning', 'error', 'critical', 'fatal']:
                return f'Invalid Parameter [{log_level}] in HTTP request -> only debug, info, warning, and error keywords are allowed.'
        except:
            log_level = None
        return ipecs.readLinesFromLogFile (num_lines=lines, log_level=None)
    else:
        return "Invalid HTTP request!"
@app.route('/system/shutdown', methods=['GET', 'HEAD'])
def shutdown () -> str:
    if ipecs is not None:
        ipecs.logout ()
        ipecs.shutdown (restart=False)
    sys.exit()
# =======================================================================================
# Test procedures
# =======================================================================================
# Test Counter reset --------------------------------------------------------------------
@app.route('/tests/reset_counters', methods=['HEAD'])
def eod_reset () -> dict:
    if not ipecs_api_is_running:
        launch_ipecs_wrapper ()
    try:
        if ipecs is not None:
            ipecs.tests_reset_counters ()
    except:
        pass
    return "All counters reset."
# Test incoming caller notification -----------------------------------------------------
@app.route('/tests/notify', methods=['POST'])
def test_notify_crm () -> None:
    if request.method != 'POST':
        return err_str_post_only
    if not ipecs_api_is_running:
        launch_ipecs_wrapper ()
    try:
        if ipecs is not None:
            station_id: int = int (request.args.get ('station'))
            call_id: int    = int (request.args.get ('callid'))
            ipecs.emit_call_notification (station_id=station_id, call_id=call_id)
            return f'Pushed call details to main Application -> Station: [{station_id}], Caller ID: [{call_id}].'
    except:
        pass
# =======================================================================================
# Simulation procedures
# =======================================================================================
# Run iPECs Login Simulation ------------------------------------------------------------
@app.route('/sim/login', methods=['POST'])
def simLogin () -> None:
    global ipecs_sim
    if dict_sim['sim_enabled']:
        loop_cnt = 1
        stn_list:list = []
        if request.method != 'POST':
            return err_str_post_only
        if not ipecs_api_is_running:
            launch_ipecs_wrapper ()
        try:
            if ipecs_sim is not None:
                stn = int (request.args.get ('station'))
                try:
                    loop_cnt = int (request.args.get ('count'))
                    if loop_cnt < 1: loop_cnt = 1
                except:
                    pass
                while loop_cnt > 0:
                    ipecs_sim.station_login (stn_id=stn)
                    stn_list.append (stn)
                    stn += 1
                    loop_cnt -= 1
            else:
                return err_str_nowrapper
        except Exception as ex:
            return f'{ex}'
        return f'Login command for station(s) {stn_list} executed successfully.'
    else:
        return f'Simulation is not enabled -> in {sim_file} section [simulation] set option sim_enabled=True'
# Simulation of station logout
@app.route('/sim/logout/station', methods=['POST'])
def simLogoutStation () -> str:
    global ipecs_sim
    if dict_sim['sim_enabled']:
        if request.method != 'POST':
            return err_str_post_only
        if not ipecs_api_is_running:
            launch_ipecs_wrapper ()
        try:
            if ipecs_sim is not None:
                stn = int (request.args.get ('station'))
                ipecs_sim.station_logout (stn_id=int (stn))
            else:
                return err_str_nowrapper
        except Exception as ex:
            return f'{ex}'
        return f'Logout command for station {stn} executed successfully.'
    else:
        return f'Simulation is not enabled -> in {sim_file} section [simulation] set option sim_enabled=True'
@app.route('/sim/logout/agent', methods=['POST'])
def simLogoutAgent () -> str:
    global ipecs_sim
    if dict_sim['sim_enabled']:
        if request.method != 'POST':
            return err_str_post_only
        if not ipecs_api_is_running:
            launch_ipecs_wrapper ()
        try:
            if ipecs_sim is not None:
                stn = int (request.args.get ('station'))
                ipecs_sim.agent_logout (stn_id=stn)
            else:
                return err_str_nowrapper
        except Exception as ex:
            return f'{ex}'
        return f'Logout command for agent {stn} executed successfully.'
    else:
        return f'Simulation is not enabled -> in {sim_file} section [simulation] set option sim_enabled=True'
# Simulate a call (incoming or outgoing)
@app.route('/sim/call', methods=['POST'])
def simCall () -> str:
    """ Simulate an incoming or outgoing call
        Request syntax: https://url/sim/call?caller_id=int&station=int&duration=int&direction=str
        caller_id: an integer number containing the simulated caller_id
        station:   the integer ID of the station to make or receive the call
        duration:  integer specifying the call duration in seconds
        direction: string specifying the call direction 'in' or 'out'

        Example: https://54.255.15.196:5000/sim/call/caller_id=91234567&station=1808&duration=120&direction=in
    """
    global ipecs_sim
    if dict_sim['sim_enabled']:
        if request.method != 'POST':
            return err_str_post_only
        if not ipecs_api_is_running:
            launch_ipecs_wrapper ()
        call_para:dict = {}
        try:
            if ipecs_sim is not None:
                call_para['caller_id']  = int (request.args.get ('caller_id'))
                call_para['station']    = int (request.args.get ('station'))
                call_para['duration']   = int (request.args.get ('duration'))
                call_para['direction']  = str (request.args.get ('direction'))
                if (call_para['direction']) == 'in':
                    ipecs_sim.make_inbound_call (call_para)
                else:
                    ipecs_sim.make_outbound_call (call_para)
                return f'Call command {call_para} executed successfully.'
            else:
                return err_str_nowrapper
        except Exception as ex:
            return f'{ex}'
        finally:
            del call_para
    else:
        return f'Simulation is not enabled -> in {sim_file} section [simulation] set option sim_enabled=True'
# Run iPECs Event Simulation ------------------------------------------------------------
@app.route('/sim/simulate_events', methods=['POST'])
def simulateEvents () -> None:
    global ipecs
    global dict_sim

    if dict_sim['sim_enabled']:
        if request.method != 'POST':
            return err_str_post_only
        if not ipecs_api_is_running:
            launch_ipecs_wrapper ()
        try:
            if ipecs is not None and dict_sim is not None:
                dict_sim['sim_rec_cnt'] = int (request.args.get ('count'))
                ipecs.simulate_events (sim_parameters=dict_sim)
            else:
                return err_str_nowrapper
        except Exception as ex:
            return f'{ex}'
    else:
        return f'Simulation is not enabled -> in {sim_file} section [simulation] set option sim_enabled=True'

@app.route('/tests/copy', methods=['POST'])
def copydata () -> None:
    ipecs.copydata ()
    return "Data copied."
# Enable or disable iPECs event processing ----------------------------------------------
@app.route('/tests/ignore_events', methods=['POST'])
def process_events () -> None:
    global ipecs
    if request.method != 'POST':
        return err_str_post_only
    if not ipecs_api_is_running:
        launch_ipecs_wrapper ()
    try:
        if ipecs is not None:
            flag = int (request.args.get ('ignore'))
            if flag > 0:
                return ipecs.setIgnoreEventsFlag ()
            else:
                return ipecs.clearIgnoreEventsFlag ()
        else:
            return (err_str_nowrapper)
    except Exception as ex:
        return f'{ex}'

# =======================================================================================
# ACD information
# =======================================================================================
@app.route('/acd_status', methods=['GET'])
def ipecsStatus () -> dict:
    if not ipecs_api_is_running:
        launch_ipecs_wrapper ()
    status = {}
    status = ipecs.getACDStatus (all_data=True)
    if status is None:
        acd_status = acdStatus.copy()
        return acd_status
    return status
# Get Call Statistics ------------------------------------------------------------------
@app.route('/acd/call_stats', methods=['GET'])
def getCallStats () -> dict:
    if not ipecs_api_is_running:
        launch_ipecs_wrapper ()
    if ipecs is not None:
        return ipecs.getCurrentStats ()
    else:
        return "System not yet started."
# =======================================================================================
# Callback functions
# =======================================================================================
def onStatusEvent (pay_load: dict) -> None:
    if pay_load is not None:
        for key in pay_load.keys():
            acdStatus[key] = pay_load[key]
def onCallWaitingEvent (pay_load: dict) -> None:
    print ("Calls waiting in queue: {0}".format (pay_load['Calls in Queue']))
def onErrorEvent (error: dict) -> None:
    global last_msg
    last_msg = error
def onSocketConnectedEvent (status: bool) -> None:
    global bool_conStatus
    bool_conStatus = status
def onSystemRecovery () -> None:
    recover_system ()
def updateSimulatorConfig (call_id: int) -> None:
    try:
        config = configparser.ConfigParser()
        fn = os.path.join(os.getcwd(), 'ipecsapiwrapper.ini')
        if os.path.exists(fn) == False:
            raise FileNotFoundError (f'iPECsAPIWrapper -> file {fn} does not exist.')
        config.read(fn)
        config.set ('simulation', 'call_ref_id', call_id)
        cf = open(fn, '+w')
        config.write (cf)
        cf.close()
        del config
    except Exception as ex:
        logging.getLogger('iPECsSimulator').error (ex)

@app.route('/', methods=['HEAD', 'GET'])
def main_entry ():
    global ipecs_api_is_running
    global main_thread
    # Check if API Wrapper is already running
    if ipecs_api_is_running:
        return (f'{__product__} version {__version__} has already been started.')
    main_thread = threading.Thread (launch_ipecs_wrapper())
    main_thread.daemon = True
    main_thread.start()
# This function will be called in case connection to server cannot be established or
# connection to server is lost in middle of operation
# It does a complete reset of the api wrapper
def recover_system ():
    global ipecs
    global ipecs_api_is_running
    if isinstance (ipecs, ipecsAPI):
        ipecs.shutdown ()
        # delete ipecs API object
        ipecs_api_is_running = False
        if main_thread.isAlive():
            main_thread.join()
            del main_thread
        ipecs_sim.shutdown()
        del ipecs
        del ipecs_sim
        # Restart iPECs API
        launch_ipecs_wrapper ()
        main_entry ()
# =======================================================================================
# Main entry point
# =======================================================================================
def launch_ipecs_wrapper ():
    global last_msg
    global log_id
    global conf_file
    global ipecs
    global ipecs_sim
    global ipecs_api_is_running
    # Check if API Wrapper is already running
    if ipecs_api_is_running:
        return (f'{__product__} version {__version__} has already been started.')
    local_logger: logging.Logger
    try:
        # Initialise the ipecs api object
        ipecs = ipecsAPI (f_name=os.path.join(os.getcwd(), conf_file), log_id=log_id, simulation_active=dict_sim['sim_enabled'], log_callback_func=onErrorEvent)
        # Get pointer to logger object
        local_logger = ipecs.Logger
        # Register call back functions
        ipecs.addEventHook (onStatusEvent)
        ipecs.addSystemResetEventHook (onSystemRecovery)
        if dict_sim['sim_enabled']:
            ipecs_sim = ipecsSim (sim_file=os.path.join(os.getcwd(), sim_file), call_id=dict_sim['call_ref_id'], mongo=ipecs.ipecsMongo, config=ipecs.ipecsConfig, ipecs=ipecs, cb_func=updateSimulatorConfig)
        #ipecs.runAPItests ()
        # Signal that the API is now running
        ipecs_api_is_running = True
        # Instruct iPECs API Wrapper to connect to iPECs server
        ipecs.connectAPI()
    # ================== Error Handling and Exit ===================================
    except KeyError as ex:
        last_msg = "[iPECs_API_Test.py --> Dictionary key not found! --> [{0}]".format(ex)
        if logging.getLevelName == logging.DEBUG:
            logging.error (msg=last_msg, exc_info=True)
        else:
            logging.error (msg=last_msg, exc_info=False)
    except Exception as ex:
        last_msg = "[iPECs_API_Test.py --> Abnormal program termination! --> [{0}]".format(ex)
        if logging.getLevelName == logging.DEBUG:
            logging.error (msg=last_msg, exc_info=True)
        else:
            logging.error (msg=last_msg, exc_info=False)
    finally:
        try:
            if isinstance (ipecs, ipecsAPI):
                ipecs.shutdown(restart=False)
                del ipecs
        except:
            pass
        try:
            if isinstance (local_logger, logging.Logger):
                del local_logger
        except:
            pass
        logging.info ('iPECs_API_Test shutdown complete.')
# =======================================================================================
if __name__ == '__main__':
    try:
        CORS (app)
        # Get basic configuration parameters
        config = configparser.ConfigParser()
        fn = os.path.join(os.getcwd(), 'ipecsapiwrapper.ini')
        config.read(fn)
        port                    = config.getint('flask', 'port')
        host_ip                 = config.get('flask', 'ip_address')
        log_id                  = config.get('config', 'log_id')
        conf_file               = config.get('config', 'config_file')
        cert_file               = config.get('ssl', 'certpath')
        key_file                = config.get('ssl', 'keypath')
        sim_file                = config.get('config', 'sim_file')  
        dict_sim['sim_enabled'] = config.getboolean('simulation', 'sim_enabled')
        if dict_sim['sim_enabled']:
            dict_sim['sim_rec_cnt']      = config.getint('simulation', 'sim_rec_cnt')
            dict_sim['sim_exec_dly']     = config.getint('simulation', 'sim_exec_dly')
            dict_sim['sim_call_len']     = config.getint('simulation', 'sim_call_len')
            dict_sim['sim_call_len_inc'] = config.getint('simulation', 'sim_call_len_inc')
            dict_sim['hold_time']        = config.getint('simulation', 'hold_time')
            dict_sim['call_ref_id']      = config.getint('simulation', 'call_ref_id')
    # Parse parameters and start app
        print (os.getcwd())
        app.run (host=host_ip, port=port, ssl_context=(cert_file, key_file))
    except Exception as ex:
        print (ex)

