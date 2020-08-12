# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import  os, sys, time, stat
tmp = os.path.join(os.getcwd(), 'lib')
paths = sys.path
try:
    paths.index (tmp)
except ValueError as ex:
    sys.path.append(tmp)

import json
import ssl, certifi
import socket, websockets, websocket, requests, urllib3
import asyncio, subprocess
import logging
import threading
import time

from datetime       import datetime
from datetime       import timedelta
from threading      import Timer
from requests.auth  import HTTPBasicAuth
from ipecs_mongo    import ipecs_db_io

try:
    from ipecs_config  import ipecs_config
except json.JSONDecodeError as ex:
    raise (ex)

STAT_0o775 = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH )

class ipecsAPI ():
# Class definitions
    _notInitErr =       "iPECsAPI ->> class ipecsAPI has not been initialised properly!"
    _config:            ipecs_config
    _mongo:             ipecs_db_io
    _ssl_context:       ssl.SSLContext
    _http:              urllib3.PoolManager
    _log:               logging.Logger
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
    _sessiontoken:      str
    _connectionTimer:   int
    _port:              int
    _isLoggedIn:        bool = False
    _isInitialised:     bool = False
    _hasServerIP:       bool = False
    _is_connected:      bool = False
    _reset_timer:       object
    _timer_first_run:   bool = True

# Call related counters
    _total_calls:       int = 0
    _handeled_calls:    int = 0
    _abandoned_calls:   int = 0
    _sum_handle_time:   float = 0.0
    _avg_handle_time:   float = 0.0    

# Initialise
    """
    Function __init__ initialises ipecsAPI class.
    
    Parameters
    ----------
    f_name : the fqdn of the iPECsAPI configuration file, default is ipecs.conf
    log_id : the name that will precede log entries in the log file and console log.

    The function will raise an exception if anything goes wrong.
    """
    def __init__ (self, f_name='res/ipecs.conf', log_id='iPECsAPI') -> None:
        self.__f_name = f_name
        try:
            # Create configuration object - that will hold all configuration information
            # This needs to be the first point of call - if not, all subsequent calls will fail
            self._config = ipecs_config (f_name, log_id)
            # Load resources
            self._log            = self._config.Logger
            self._cmds           = self._config.getiPECsCommands ()
            self._cmd_ary        = self._config.getiPECsCommandArray ()
            self._baseURIExt     = self._config.getBaseURIExt ()
            self._baseURI        = self._config.ipecs_uri_base
            self._port           = self._config.ipecs_port
            self._fullURI        = self._config.getFullURI ()
            self._baseWSS        = self._config.ipecs_wss_base
            self._srvIP          = self._config.getiPECsServerIP ()
            self._fullWSS        = self._config.ipecs_wss_full.format (self._srvIP, self._config.ipecs_port, self._config.ipecs_uid)
            self._timeout        = self._config.ipecs_timeout
            self._retry_attempts = self._config.ipecs_retry_attempts
            self._retry_rate     = self._config.ipecs_retry_rate

        # Create a Timer that will reset all counters to 0 at a time defined in the configuration file
            self._init_Reset_Timer ()

        # Make sure to avoid SSl errors
            if self._config.ipecs_disable_SSL_warnings:
                if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
                    self._log.info (self._config.getResourceString('inf', 'inf003'))
                    ssl._create_default_https_context = ssl._create_unverified_context
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            else:
                urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ce_certs=certifi.where())
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
            self._mongo = ipecs_db_io (self._config.getResources ('mongo'), self._config.getSection ('mongo'), self._log)
    # Initialisation complete - we can use his class now 
            self._log.debug (self._config.getResourceString('msg', 'msg003').format(self.__class__))
            self._isInitialised = True
        except ValueError as ex:
            self._log.fatal (ex)
            raise Exception (ex)
        except Exception as ex:
            self._log.fatal (ex, exc_info=False)
            raise Exception (ex)

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
    def shutdown (self)-> None:
        if isinstance (self._config, ipecs_config):
            if self._isLoggedIn:
                self._log.info (self._config.getResourceString ('http', 'http012').format (self._baseURIExt))
                #TODO uncomment self.logout ()
            # shutdown the config object -> this will make sure that any changes will get saved before deleting the object 
            self._config.shutdown ()
        self.__del__()

    def getConfiguration (self, section=None) -> dict:
        return self._config.getSection (section)

    def getResources (self, section=None) -> dict:
        return self._config.getResources (section)
    
    def getResourceString (self, section, key) -> str:
        return self._config.getResourceString (section, key)

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

# Call counter reset function
    def _resetCounters (self) -> None:
        try:
            self._log.info (self._config.getResourceString ('inf', 'inf007'))
            self._mongo
            self._total_calls       = 0
            self._abandoned_calls   = 0
            self._handeled_calls    = 0
            self._avg_handle_time   = 0.0
            self._sum_handle_time   = 0.0
            pass
        except:
            pass
        finally:
            # restart timer
            self._init_Reset_Timer ()

# Initialise and start reset timer
    def _init_Reset_Timer (self) -> None:
        reset_time = time.strptime (self._config.ipecs_metrics_reset_time, '%H:%M:%S')
        # If this is the first run, do not add a new day to the rest timer, first reset will occur same day as API is run
        if self._timer_first_run:
            x = datetime.now()
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
        secs = delta_t.total_seconds ()

        self._reset_timer = Timer (secs, self._resetCounters)
        self._reset_timer.start()
        self._log.info (self._config.getResourceString ('inf', 'inf008').format (y.strftime ('%Y-%m-%d'), y.strftime ('%H:%M:%S')))


# isUserLoggedIn - Check if user is checked in
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

# _httpCheckResponse - Helper function to check HTTP response for errors
    """
    Function _httpCheckResponse checks the HTTP response received from a http request sent.
    It will log the error details in the logger and then throw an exception of type <requests.exceptions.HTTPError>
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

# logErrorMsg - Helper function to log error message received from iPECs API
    """
    Function logErrorMsg() -> None logs an error received from iPECsAPI to log file.
    The function will raise an exception if the expected keys cannot be found in the error response.
    
    Parameters
    ----------
    response : type <http error response>.

    Returns:
    ----------
    None:    
    """
    def logErrorMsg (self, response) -> None:
        try:
            json = response.json()
            msg = self._config.getResourceString('ipecs', 'error').format(json['error']['code'], json['error']['message'])
            self._log.error (msg)
        except KeyError as ex:
            self._log.error (self._config.getResourceString('err', 'err002').format(ex))
            raise KeyError (ex)

# sendCommand - Function filters, prepares parameters and sends command to be send to iPECs API to appropriate command function
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

# login - Send login command to iPECs Server API
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
        _time_start = datetime.now()
        # Make sure this class is fully initialised
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        # Check if user is already logged in - if yes, do nothing and return
        if self._isLoggedIn:
            self._log.info (self._config.getResourceString('http', 'http001'))
            return
        try:
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
                    self._log.debug(self._config.getResourceString('http', 'http008').format(response.status_code, _retry_rate))
                    time.sleep (_retry_rate)
                    continue
                # Check if the response is a 401 - means the user is already logged on or not authorised
                if response.status_code == 401:
                    # We have reached the maximum number of retries, bail out
                    if i == _retry_attempts - 1:
                        self._isLoggedIn = False
                        raise self.LoginRetryAttemptsExceeded (self._config.getResourceString('http', 'http006').format(self._baseURIExt, self._config.ipecs_port, _retry_attempts))
                    else:
                        json = response.json()
                        if json['error']['code'] == 2: # Invalid login information
                            raise ValueError (self._config.getResourceString('err', 'err007').format(self._baseURIExt))
                        else:
                            # There is a timeout, could be that a user is already logged in - retry
                            self._log.warning(self._config.getResourceString('http', 'http007').format(response.status_code, _retry_rate, json['error']['message'], i+2))
                            time.sleep (_retry_rate)
                else:
                    # This is not a 401 response, so let's check what we have - the check will throw an exception if response is not 200 
                    self._httpCheckResponse (response, _cmd, self._baseURIExt)
                    # Get the response
                    resp = response.json()
                    # Get the token
                    self._sessiontoken = resp['token']
                    # get the timeout reported by the server
                    self._connectionTimer = resp['checkConnectionTimer']
                    self._log.info (self._config.getResourceString ('http', 'http010').format (self._baseURIExt, resp['checkConnectionTimer'], resp['systemType'], resp['systemVersion'], resp['apiVersion']))
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
            _time_end = datetime.now()
            _time_diff = _time_end - _time_start
            self._log.info (self._config.getResourceString ('inf', 'inf006').format ('login', _time_diff.total_seconds()))
            if isinstance (_user, str):
                del _user
            if isinstance (_password, str):
                del _password
            if isinstance (_header, dict):
                del _header
            if isinstance (_cmd, str):
                del _cmd

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

# logout - Send logout command to iPECs Server API
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
    def logout (self) -> None:
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        if not self._isLoggedIn:
            self._log.debug (self._config.getResourceString('http', 'http002').format('logout'))
            return
        try:
            cmd = self._cmds['logout'].format(self._fullURI, self._config.ipecs_uid)
            self._log.debug (self._config.getResourceString('inf', 'inf002').format(cmd))
            try:
                hed = self._config.getiPECsHeader('hdr_logout')
                hed['Authorization'].value = hed['Authorization'].value.format (self._sessiontoken)
                response = requests.post(cmd, headers=hed, verify=self._config.ipecs_verify)
                self._httpCheckResponse (response, cmd, self._baseURIExt)
            except urllib3.exceptions.InsecureRequestWarning as ex:
                self._log.error (ex)
            except requests.exceptions.SSLError as ex:
                self._log.error (ex)
            finally:
                del hed
        except KeyError as ex:
            self._log.error (self._config.getResourceString('err', 'err002').format (ex))
        except Exception as ex:
            self._log.critical (ex)
        finally:
            self._isLoggedIn = False
            del cmd
    
# smdr - Send SMDR command to iPECs Server API
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
#                   DEFINITION FOR IPECS_WEBSOCKET
# -------------------------------------------------------------------------------------------------
# Start Socket Listener
    def startSocketListener (self):
        self._log.debug (self._config.getResourceString('http', 'wss011'))
        try:
            asyncio.get_event_loop().run_until_complete(asyncio.wait([self.alive(), self.ipecsSocketListener()]))
        except:
            self._has_error = True
        if self._has_error and not self._is_connected: 
            raise ipecsAPI.ConnectionClosed (self._config.getResourceString('http', 'wss009').format(self._srvIP))
        self._is_connected = True
        self._log.info (self._config.getResourceString('http', 'wss008').format(self._srvIP))

# Async Functions
    async def alive(self):
        while self._is_connected:
            self._log.info('alive')
            await asyncio.sleep(self._config.ipecs_socket_timeout)

    async def ipecsSocketListener (self):
        """async_processing starts the asynchronous process to listen to the socket connection

        Raises:
            self.ConnectionRefused: raised when the server refuses the connection
            self.ConnectionClosed:  raised when the server closes the connection
        """
        _thread_id = 1
        try:
            hed = self._config.getiPECsHeader ('hdr_wss')
            hed['Authorization'] = hed['Authorization'].format (self._sessiontoken)
            hed['Origin'] = hed['Origin'].format (self._baseURI, self._port)
            if self._log.level is logging.DEBUG:
                self._log.debug ("Socket Connection Parameters are: [{0}] - [{1}] ".format (self._fullWSS, hed))
            async with websockets.connect(
                self._fullWSS, 
                ssl=self._ssl_context, 
                ping_interval=self._config.ipecs_socket_timeout * 0.95, 
                ping_timeout=self._config.ipecs_ping_timeout,
                extra_headers=hed) as websocket:
                self._log.info (self._config.getResourceString ('http', 'wss008').format (self._srvIP))
                while True:
                    try:
                        message = await websocket.recv()
                        self._thread = ipecsAPI.iPECsEventDigestThread (_thread_id, json.loads(message), self._log, self._config)
                        self._thread.setDaemon
                        self._thread.setName ('iPECs Event Digest')
                        self._thread.run ()
                        _thread_id += 1
                    except json.JSONDecodeError as ex:
                        self._log.warning (self._config.getResourceString ('http', 'wss016').format (message))
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        self._log.warning (self._config.getResourceString('http', 'wss014').format (self._srvIP))
                        self._is_connected = False
                        break
        except websockets.exceptions.InvalidStatusCode as ex:
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
                raise self.ConnectionRefused (err, code)
        except Exception as ex:
            self._has_error = True
            raise self.ConnectionClosed (ex)

# -------------------------------------------------------------------------------------------------
#                   DEFINITION FOR IPECS_API CALLBACK FUNCTIONS
# -------------------------------------------------------------------------------------------------
    def onNewCallEvent (self) -> dict:
        pass

# -------------------------------------------------------------------------------------------------
#                   DEFINITION FOR IPECS_API THREADING FUNCTIONS
# -------------------------------------------------------------------------------------------------
    def iPECsDigestEvent (self, event: dict, logger: logging.Logger, config: ipecs_config) -> None:
        """iPECsDigestEvent analyses the Event data returned by the server through the socket connection.
        This code runs as a thread.

        Args:
            event (dict): the event data received from the server

        Raises:
            exception: 
            UnknownEventFormat - if flag to raise exception is set in config file
            Otherwise the function creates a log entry with the raw event data
        """
        # check if the event data is formated as a dictionary
        if isinstance (event, dict) and event is not None:
            # Check that this event data is in fact from the iPECs acd engine
            try:
                for key in event.keys():
                    if key == 'event':
                        if event[key] == 'acd':
                            continue
                    if key == 'data':
                        # This is a server ping
                        if event[key]['eventCode'] == 68:
                            logger.debug (config.getResourceString ('http', 'wss018'))
                            break
                        # Incoming Call
                        if event[key]['eventCode'] == 72:
                            self._total_calls += 1

                        
        # TODO: write code to disgest event

                            pass
            except Exception as ex:
                logger.warning (config.getResourceString ('http', 'wss016').format (event, ex))
            # Signal the this thread as completed
            logger.debug (config.getResourceString ('http', 'wss017'))
            pass
        else:
            # Log an error or raise exception that event data received from server is not as expected
            err = self._config.getResourceString ('http', 'wss016').format (event)
            # if fail-on-event-data-malformat flag is true, raise an exception
            if config.ipecs_fail_on_event_malformat:
                raise self.UnknownEventFormat (err)
            else:
                # log warning and return
                logger.warning (err)
                return
        return

    class iPECsEventDigestThread (threading.Thread):
        def __init__ (self, threadID:int, event: dict, logger: logging.Logger, config: ipecs_config):
            threading.Thread.__init__(self)
            self.threadID = threadID
            self.name = 'iPECsEventDigestThread'
            self.event = event
            self.config = config
            self._log = logger
        def run (self):
            ipecsAPI.iPECsDigestEvent (self, self.event, self._log, self.config)

# -------------------------------------------------------------------------------------------------
#                   DEFINITION FOR IPECS_API CUSTOM EXCEPTIONS
# -------------------------------------------------------------------------------------------------
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
                self.status_code = args[1]
            else:
                self.message = "Server refused connection."

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
