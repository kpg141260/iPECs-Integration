# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

# Class presenting a json configuration file in the form of properties such as ipecs_config.key1.value1
# instead of having to use the more typing involved ipecs_config['key1']['value1']

import json, os, sys, logging
import logging, datetime, time
import websockets, socket

from    logging.handlers    import RotatingFileHandler
from    logging             import StreamHandler
from    __version           import __version__, __product__
#from    ipecs_crypt         import ipecs_crypt

LOGGING_ID = 'iPECsAPI'

class ipecs_config ():
# Class wide private varables
# Initialise class ipecs_config
    def __init__ (self, config_file_name, log_id=LOGGING_ID, log_callback_function=None):
        self._notInitErr =       "iPECsAPI ->> class ipecsAPI has not been initialised properly!"
        self._config:            dict # the JSON dictionary to be loaded
        #_cipher:               ipecs_crypt
        self._log:               logging.Logger
        self._log_callback:      object
        self._resources:         dict
        self._comands:           dict
        self._headers:           dict
        self._responses:         dict
        self._error_codes:       dict
        self._event_codes:       dict
        self._call_types:        dict
        self._conf_act_types:    dict
        self._call_fwd_types:    dict
        self._ringing_types:     dict
        self._opcodes:           dict
        self._station_status:    dict
        self._station_summary:   dict
        self._acd_summary:       dict
        self._acd_history:       dict
        self._call_summary:      dict
        self._missed_call:       dict
        self._ary_commands:      list
        self._ary_keys_cnf:      list
        self._ary_error_codes:   list
        self._ary_event_codes:   list
        self._ary_call_types:    list
        self._ary_conf_act_types:list
        self._ary_call_fwd_types:list
        self._ary_ringing_types: list
        self._ary_sect_res:      list
        self._f_name:            str  # the fqfn of the configuration file
        self._srvIP:             str
        self._baseURI:           str
        self._fullURI:           str
        self._event_time_format: str
        self._hasChanges:        bool
        self._isInitialised:     bool = False
        try:
            init_start = time.perf_counter ()
            self._hasChanges    = False
            self._f_name        = config_file_name
            self._log_callback  = log_callback_function
            # Make sure file exists
            if os.path.exists(self._f_name) == False:
                logging.fatal(f"iPECsAPI ->> Can't find input file {self._f_name}. Execution cannot continue!")
                # File does not exist, cannot continue - bail out
                raise FileNotFoundError (self._f_name)
            else:
                # All good, read file
                with open (self._f_name, 'r') as json_file:
                    data = json_file.read()
                # Parse file data    
                self._config        = json.loads(data)
                self._ary_keys_cnf  = list (self._config.keys())
                self.config_logger (log_id)
                self._log = logging.getLogger (LOGGING_ID)
                self._loadResourceFile ()
                self._loadCommandsFile ()
                # Create ipecs_crypt object -> we need that in any case
                #self._cipher = ipecs_crypt(self._config['resource']['key-file'], self._resources['cipher'], logger=self._log)
                self._log.debug (self._resources['msg']['msg003'].format(self.__class__, time.perf_counter () - init_start))
                self._isInitialised = True
        except json.JSONDecodeError as ex:
            logging.fatal ("iPECsAPI ->> JSON decoding error while processing [{0}]!".format (self._f_name))
            ex._module_ = self.__module__
            ex._class_  = self.__class__
            raise Exception (ex, exc_info=True)
        except PermissionError as ex:
            ex._module_ = self.__module__
            ex._class_  = self.__class__
            raise Exception (ex)
        except Exception as ex:
            ex._module_ = self.__module__
            ex._class_  = self.__class__
            raise Exception (ex)
# Delete self method
    def __del__ (self):
        try:
            self._log.debug (self._resources['inf']['inf005'])
        except:
            pass
        # Make sure we save any changes before destroying the class
        try:
            if self._hasChanges:
                self.saveConfiguration ()
        except:
            pass
        try:
            if isinstance (self._config, dict):
                del self._config
        except:
            pass
        try:
            if isinstance (self._ary_keys_cnf, list):
                del self._ary_keys_cnf
        except:
            pass
        try:
            if isinstance (self._comands, dict):
                del self._comands
        except:
            pass
        try:
            if isinstance (self._ary_commands, list):
                del self._ary_commands
        except:
            pass
        try:
            if isinstance (self._ary_error_codes, list):
                del self._ary_error_codes
        except:
            pass
        try:
            if isinstance (self._ary_event_codes, list):
                del self._ary_event_codes
        except:
            pass
        try:
            if isinstance (self._ary_call_types, list):
                del self._ary_call_types
        except:
            pass
        try:
            if isinstance (self._ary_conf_act_types, list):
                del self._ary_conf_act_types
        except:
            pass
        try:
            if isinstance (self._ary_call_fwd_types, list):
                del self._ary_call_fwd_types
        except:
            pass
        try:
            if isinstance (self._ary_ringing_types, list):
                del self._ary_ringing_types
        except:
            pass
        try:
            if isinstance (self._headers, dict):
                del self._headers
        except:
            pass
        try:
            if isinstance (self._responses, dict):
                del self._responses
        except:
            pass
        try:
            if isinstance (self._error_codes,  dict):
                del self._error_codes
        except:
            pass
        try:
            if isinstance (self._event_codes, dict):
                del self._event_codes
        except:
            pass
        try:
            if isinstance (self._call_types, dict):
                del self._call_types
        except:
            pass
        try:
            if isinstance (self._call_fwd_types, dict):
                del self._call_fwd_types
        except:
            pass
        try:
            if isinstance (self._ringing_types, dict): 
                del self._ringing_types
        except:
            pass
        try:
            if isinstance (self._opcodes, dict):
                del self._opcodes
        except:
            pass
        try:
            if isinstance (self._srvIP, str):
                del self._srvIP
        except:
            pass
        try:
            if isinstance (self._baseURI, str):
                del self._baseURI
        except:
            pass
        try:
            if isinstance (self._fullURI, str):
                del self._fullURI
        except:
            pass
        try:
            if isinstance (self._acd_summary, str):
                del self._acd_summary
        except:
            pass
        try:
            if isinstance (self._acd_history, str):
                del self._acd_history
        except:
            pass
        try:
            self._log.info (self._resources['inf']['inf009'])
            if isinstance (self._resources, dict):
                del self._resources
            logging.shutdown()
        except:
            pass
        try:
            if isinstance (self._log, logging.Logger):
                del self._log
        except:
            pass
# saveConfiguration - saves configuration changes to file
    def saveConfiguration (self):
        if not self._hasChanges:
            return
        self._log.info (self._resources['inf']['inf010'])
        # Do we need to backup the existing configuration file?
        if self._config['options']['backup-count'] > 0:
            # Create backup file name
            _f_tmp = self._f_name + '.bak'
            # Check if there already is a file with that name
            if os.path.exists (_f_tmp):
                # create a list
                cnt = self._config['options']['backup-count']
                files = []
                files.append (_f_tmp)
                for i in range (1, cnt, 1):
                    files.append (_f_tmp + '.' + str (i))
                    # Check if this file exists
                    if os.path.exists (files[i]):
                        # Yes it does, continue
                        continue
                    # Reached count of permissible backup files?
                    if i == cnt:
                        os.remove (files[i])
                # Now go through the array and rename all the files
                for i in range (0, len(files), 1):
                    if i == 0:
                        # this is the file with.bak change to .bak.1
                        os.rename (files[i], files[i] + '.' + str (i+1))
                    else:
                        # this is a file with .bak.n -> replace .bak.n with .bak.n+1
                        os.rename (files[i], files[i].replace (str(i), str (i + 1)))
                if isinstance (files, list):
                    del files
            # Now we got all this out of the way, let's create the backup
            os.rename (self._f_name, self._f_name + '.bak')
        # No backups required let's just overwrite the existing file
        with open (self._f_name, 'w+') as json_file:
            json_file.write(json.dumps(self._config, indent=4))
            json_file.close()
            self._log.info (self._resources['inf']['inf011'])
            self._hasChanges = False
# Shutdown   
    def shutdown (self) -> None:
        return
        #if isinstance (self._cipher, ipecs_config) and self._isInitialised:
        #    self._cipher.shutdown()
        #    del self._cipher
        #self.__del__()

    def getConfig (self):
        return (self)
# config_logger - Configure Logger
    """
    Function config_logger()  -> logging.Logger.
    
    Parameters
    ----------
    id : the name that will precede log entries in the log file and console log.

    The function creates and formats 1 or 2 logging streams. 1 to console, which can be switched off in the config file,
    and 1 to a log file. the formatting for the loggers are all defined in the configuration file specified in the 
    __init__ function.
    """
    def config_logger (self, id) -> logging.Logger:
        logger: logging.Logger
        try:
            truncated = False
            f_log = self.log_file_name
            log_path = os.path.join (os.getcwd(), self.log_path)
            if os.path.exists (log_path) == False:
                os.makedirs (log_path, mode=0o766, exist_ok=True)
            # Check if log-file exists
            if os.path.exists(f_log) == False:
                fp = open (f_log, "w+")
                os.chmod (f_log, mode=0o766)
                fp.close()
            else:
                # Check file size and truncate if required
                f_size = os.path.getsize(f_log)
                if f_size > self.log_file_max_size and self.log_file_truncate and not self.log_file_rotate:
                    # truncate the file
                    fp = open (f_log, 'w')
                    truncated = True
                    fp.close()
            formatter = logging.Formatter (fmt=self.log_format, datefmt=self.log_date_format)
            # Setup logging to callback function -> last log message will be available through Flask /last_msg method
            logger = logging.getLogger(id)
            if self.event_simulation:
                sim_logger = logging.Logger ('iPECsSimulator')
            if self._log_callback is not None:
                ilh = iPECsLoggingHandler (self._log_callback)
                ilh.setLevel(logging.INFO)
                ilh.setFormatter (formatter)
                logger.addHandler (ilh)
                if self.event_simulation:
                    sim_logger.addHandler (ilh)
            # Enable logging to file
            if self.log_to_file:
                # Add rotating log file handler for ipECsApi
                logger.setLevel(self.log_level)
                if (self.log_file_rotate):
                    file_handler = RotatingFileHandler(f_log, maxBytes=self.log_file_max_size, backupCount=self.log_file_count)
                else:
                    file_handler = logging.FileHandler(f_log)
                logger.addHandler(file_handler)
                if self.event_simulation:
                    sim_logger.addHandler(file_handler)
                # Add log file formatter
                if (self.log_level == "DEBUG"):
                    formatter = logging.Formatter (fmt=self.log_format_debug, datefmt=self.log_date_format)
                file_handler.setFormatter (formatter)
            else:
                if (self.log_level == "DEBUG"):
                    logging.basicConfig(level=self.log_level, format=self.log_format_debug, datefmt=self.log_date_format)
                else:
                    logging.basicConfig(level=self.log_level, format=self.log_format, datefmt=self.log_date_format)
            # if log-to-file is false, enforce stdout logger regardless of log-to-stdout flag
            if (not self.log_to_stdout and not self.log_to_file) or self.log_to_stdout:
                consoleHandler = logging.StreamHandler()
                consoleHandler.setLevel(self.log_level)
                logger.addHandler(consoleHandler)
                if self.event_simulation:
                    sim_logger.addHandler(consoleHandler)
                if (self.log_level == "DEBUG"):
                    formatter = logging.Formatter(fmt=self.log_format_debug, datefmt=self.log_date_format)
                consoleHandler.setFormatter(formatter)
            version = '.'.join(str(c) for c in __version__)
            logger.info (f'{__product__} version {version} loaded.')
            logger.debug ("Log system activated.")
            if (truncated):
                logger.warning (f'Log-file has been truncated! - Previous log-entries purged!')
            del f_log
            return logger
        except FileExistsError as ex:
            logging.fatal ("iPECsAPI -> File does not exist.")
        except PermissionError as ex:
            raise ("iPECsAPI -> File permission error - cannot create log file.")
        except Exception as ex:
            raise (ex)
# loadResourceFile - Load Resource File
    """
    Function loadResourceFile() -> None.
    
    Parameters
    ----------
    none : nil.

    The function loads the language resource file defined in the configuration file specified in the __init__ function.
    """
    def _loadResourceFile (self) -> None:
        try:
            cwd = os.getcwd()
            f_res = os.path.join (cwd, self.resource_file)
            # Check if resource-file exists
            if os.path.exists(f_res) == False:
                raise FileNotFoundError ("The language resource file {0} could not be found. Execution halted!".format(f_res))
            with open (f_res, 'r') as json_file:
                data = json_file.read()
            # Parse file data 
            json_file.close()
            self._resources    = json.loads(data)
            self._ary_sect_res = list (self._resources.keys())
            self._log.info (self._resources['msg']['msg001'].format (f_res))
            del f_res
        except PermissionError as ex:
            logging.fatal ("iPECsAPI -> File {0} permission error.".format(f_res))
        except Exception as ex:
            raise (f'{__class__}._loadResourceFile -> {ex}')
# _saveSessionToken - Save Session Token to File
    """
    Function saveSessionToken() -> None.
    
    Parameters
    ----------
    @token : str

    The function saves the current session token to file.
    """
    def _saveSessionToken (self, token: str) -> None:
        try:
            t_dict = {'token': token}
            cwd = os.getcwd()
            f_name = os.path.join (cwd, self._config['resource']['token-file'])
            with open (f_name, 'w+') as json_file:
                json_file.write(json.dumps(t_dict))
                json_file.close()
                del f_name
        except PermissionError as ex:
            self._log.error (self._resources['err']['err010'].format(f_name, ex))
        except Exception as ex:
            self._log.warning (self._resources['warn']['wrn002'].format (ex)) 
# _getSessionToken - Save Session Token to File
    """
    Function getSessionToken() -> None.
    
    Parameters
    ----------
    None : nil

    Returns
    -------
    @SessionToken: dict

    The function retrieves the last session token from file.
    """
    def _getSessionToken (self) -> dict:
        try:
            cwd = os.getcwd()
            f_name = os.path.join (cwd, self._config['resource']['token-file'])
            # Check if resource-file exists
            if os.path.exists(f_name) == False:
                self._log.warning (self._resources['warn']['wrn001']) 
            with open (f_name, 'r') as json_file:
                data = json_file.read()
            # Parse file data    
            t = json.loads(data)
            json_file.close()
            token = t['token']
            self._log.info (self._resources['msg']['msg004'].format (f_name))
            return token
        except PermissionError as ex:
            self._log.error (self._resources['err']['err010'].format(f_name, ex))
        except Exception as ex:
            self._log.warning (self._resources['warn']['wrn002'].format (ex)) 
        finally:
            del f_name
# loadCommandsFile - Load iPECs Commands and Headers File
    """
    Function loadCommandsFile() -> None.
    
    Parameters
    ----------
    none : nil.

    The function loads the language resource file defined in the configuration file specified in the __init__ function.
    """
    def _loadCommandsFile (self) -> None:
        try:
            f_cmd = os.path.join (os.getcwd(), self.command_file)
            # Check if resource-file exists
            if os.path.exists(f_cmd) == False:
                raise FileNotFoundError (self._resources['err']['err003'].format(f_cmd))
            with open (f_cmd, 'r') as json_file:
                data = json_file.read()
            # Parse file data
            self._ipecs                 = json.loads(data)
            self._comands               = self._ipecs['commands']
            self._ary_commands          = list(self._comands.keys())
            self._headers               = self._ipecs['headers']
            self._responses             = self._ipecs['responses']
            self._error_codes           = self._ipecs['error-codes']
            self._ary_error_codes       = list (self._error_codes.keys())
            self._event_codes           = self._ipecs['event-codes']
            self._ary_event_codes       = list (self._event_codes.keys())
            self._call_types            = self._ipecs['call-types']
            self._ary_call_types        = list (self._call_types.keys())
            self._conf_act_types        = self._ipecs['conf-action-types']
            self._ary_conf_act_types    = list (self._conf_act_types.keys())
            self._call_fwd_types        = self._ipecs['call-forward-types']
            self._ary_call_fwd_types    = list (self._call_fwd_types.keys())
            self._ringing_types         = self._ipecs['ringing-types']
            self._ary_ringing_types     = list (self._ringing_types.keys())
            self._opcodes               = self._ipecs['op-codes']
            self._event_time_format     = self._ipecs['event-time-format']
            self._station_status        = self._ipecs['station-status']
            self._agent_summary         = self._ipecs['agent-summary']
            self._acd_summary           = self._ipecs['acd-summary']
            self._acd_history           = self._ipecs['acd-history']
            self._call_summary          = self._ipecs['call-summary']
            self._missed_call           = self._ipecs['missed-call']

            self._log.info (self._resources['msg']['msg002'].format (f_cmd))
            del f_cmd

        except PermissionError as ex:
            logging.fatal (f'iPECsAPI -> File {f_cmd} permission error.')
        except Exception as ex:
            logging.error (f'iPECsAPI -> {ex}.')
            raise (ex)
# getBaseURIExt - Get Base URI from Config File
    """
    Function getBaseURIExt() -> string.
    
    Parameters
    ----------
    none : nil.

    The function generates, stores locally and returns the base URI pointing the the iPECs API server.
    The parameters are defined in the configuration file specified in the __init__ function.
    """
    def getBaseURIExt (self) -> str:
        self._baseURI = "{}:{}/{}/".format(self.ipecs_uri_base, self.ipecs_port, self.ipecs_type)
        self._log.debug ((self._resources['dbg']['dbg001']).format (self._baseURI))
        return (self._baseURI)
# getFullURI - Get Full URI from Config File
    """
    Function getFullURI() -> string.
    
    Parameters
    ----------
    user : the name of the user to be included in the fully qualified command string (fqcs).

    The function generates, stores locally and returns the fully qualified URI that needs to be send to the iPECs API server
    for command execution; however, does not yet populate the actual command.

    Sample command: /ipxapi/server/v1/users/apiadmin/[command]

    The parameters for the function are defined in the configuration file specified in the __init__ function.
    """
    def getFullURI (self, user='admin') -> str:
        if user == 'admin':
            self._fullURI = "{}{}/{}/users/".format(self.getBaseURIExt(), self.ipecs_target, self.ipecs_api_version)
        else:
            self._fullURI = "{}{}/users/".format(self.getBaseURIExt(), self.ipecs_api_version)
        self._log.debug ((self._resources['dbg']['dbg002']).format (self._fullURI))
        return (self._fullURI)
# getbaseWSS - Get base WSS (secure socket address)
    """
    Function getbaseWSS() -> string.
    
    Parameters
    ----------
    none : nil

    The function generates, stores locally and returns the fully qualified web socket address for the iPECs API server.

    Returns:
    ----------
    web socket connection string : <string> web socket address in the form of wss://192.192.192.2:6666/ipxapi
    """
    def getbaseWSS (self) -> str:
        try:
            if not self._hasServerIP:
                self.getiPECsServerIP
            wss = self.ipecs_wss_base.format (self._srvIP, self.ipecs_port)
            self._log.debug (self._resources['dbg']['dbg004'].format(wss))
            return wss
        except Exception as ex:
            raise (ex) 
# getWSSURI - Get full WSS URI (secure socket address)
    """
    Function getbaseWSS() -> string.
    
    Parameters
    ----------
    none : nil

    The function generates, stores locally and returns the fully qualified web socket address for the iPECs API server.

    Returns:
    ----------
    web socket connection string : <string> web socket address in the form of wss://192.192.192.2:6666/ipxapi
    """
    def getfullWSS (self) -> str:
        try:
            if not self._hasServerIP:
                self.getiPECsServerIP
            wss = self.ipecs_wss_full.format (self._srvIP, self.ipecs_port, self._get_user_id ('ipecs'))
            self._log.debug (self._resources['dbg']['dbg004'].format(wss))
            return wss
        except Exception as ex:
            raise (ex) 
# getiPECsServerIP - Get IP address of ipecs server
    """
    Function getiPECsServerIP.
    
    Parameters
    ----------
    none : nil.

    The function returns the IP address of the iPECs API server specified in the configuration file.
    Function will throw an exception if an error occurs.
    """
    def getiPECsServerIP (self) -> str:
        try:
            if self.ipecs_uri_base.startswith('https://'):
                host = self.ipecs_uri_base.replace('https://', '')
            else:
                host = self.ipecs_uri_base
            self._srvIP = socket.gethostbyname (host)
            self._log.info (self._resources['inf']['inf001'].format (host, self._srvIP))
            self._hasServerIP = True
            # Save last known ip address
            self.ipecs_set_ip (address=self._srvIP)
            return self._srvIP
        except socket.error as ex:
            self._hasServerIP = False
            raise ConnectionError (self._resources['err']['err001'].format (host, ex))
        finally:
            del host
    
    def is_iPECsPortOpen (self, ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((ip, int (port)))
            s.shutdown (2)
            return True
        except:
            return False
# Resources - Provide pointers to language resources
    """
    Function getResources() -> dictionary.
    
    Parameters
    ----------
    section :   <str> specifies the sub-section of the dictionary to return.
                default is to return all sections.

    The function returns an object of type {dict} containing the language strings.
    """
    def getResources (self, section=None) -> dict:
        if section is None:
            return self._resources
        for key in self._resources.items():
            if key[0] == section:
                return self._resources[section]
        raise KeyError (self._resources['err']['err002'].format(key, section))
    def getResourceString (self, section, key) -> str:
        try:
            self._ary_sect_res.index(section)
            return self._resources[section][key]
        except:
            raise KeyError (self._resources['err']['err002'].format(key, section))
    def getiPECsCommands (self, section=None) -> dict:
        try:
            if section == None:
                return self._comands
            elif list(self._comands.keys()).index(section):
                return self._comands[section]
        except:
            raise KeyError (self._resources['err']['err002'].format(section, self.command_file))
    def getDictStationStatus (self) -> dict:
        return self._station_status
    def getDictAgentSummary (self) -> dict:
        return self._agent_summary
    def getDictACDSummary (self) -> dict:
        return self._acd_summary
    def getDictACDHistory (self) -> dict:
        return self._acd_history
    def getDictCallSummary (self) -> dict:
        cs = self._ipecs['call-summary']
        return cs
    def getMissedCallDict (self) -> dict:
        return self._missed_call
    def getiPECsHeader (self, header):
        try:
            return self._headers[header]
        except:
            raise KeyError (self._resources['err']['err002'].format(header, self.command_file))
    def getiPECsResponse (self, response: str) -> dict:
        try:
            return self._responses[response]
        except:
            raise KeyError (self._resources['err']['err002'].format(response, self.command_file))
    def getiPECsCommandArray (self) -> list:
        return list(self._comands.keys())
    def getiPECsEventCodes (self):
        return self._event_codes
    def getiPECsEventCodeString (self, key) -> str:
        try:
            self._ary_event_codes.index(key)
            return self._event_codes[key]
        except:
            return self._resources['ipecs']['wrn002']
    def getiPECsErrorCodeString (self, key) -> str:
        try:
            self._ary_error_codes.index(key)
            return self._event_codes[key]
        except:
            return self._resources['ipecs']['wrn003']
    def getiPECsCallTypeString (self, key) -> str:
        try:
            self._ary_call_types.index(key)
            return self._call_types[key]
        except:
            return self._resources['ipecs']['wrn004']
    def getiPECsConferenceActionTypeString (self, key) -> str:
        try:
            self._ary_conf_act_types.index(key)
            return self._conf_act_types[key]
        except:
            return self._resources['ipecs']['wrn005']
    def getiPECsCallForwardTypeString (self, key) -> str:
        try:
            self._ary_call_fwd_types.index(key)
            return self._call_fwd_types[key]
        except:
            return self._resources['ipecs']['wrn006']
    def getiPECsRingingTypeString (self, key) -> str:
        try:
            self._ary_ringing_types.index(key)
            return self._ringing_types[key]
        except:
            return self._resources['ipecs']['wrn007']
    def getiPECsErrorCodes (self):
        return self._error_codes
    def getiPECsCallTypes (self):
        return self._call_types
    def getiPECsConferenceActionTypes (self):
        return self._conf_act_types
    def getiPECsCallForwardTypes (self):
        return self._call_fwd_types
    def getiPECsRingingTypes (self):
        return self._ringing_types
    def keys (self):
        return self._ary_keys_cnf
    def getSection (self, section=None) -> dict:
        try:
            # if no section defined, return the whole config dictionary
            if section is None:
                return self._config
            else:
                # Index will raise an exception if key not found, 
                # so the return wil only execute if key is found 
                self._ary_keys_cnf.index(section)
                return self._config[section]
        except:
            raise KeyError ("{self.__class__.__name__} -> {0}".format (self._resources['err']['err002'], section, 'ipecs.conf'))  
# iPECs API Wrapper Interface related properties
    @property
    def ipecs_responses (self) -> dict:
        return self._responses
    @property
    def ipecs_headers (self) -> dict:
        return self._headers
    @property
    def ipecs_op_codes (self) -> dict:
        return self._opcodes
    @property
    def ipecs_uri_base (self) -> str:
        return self._config['ipecs']['BaseURI']
    @property
    def ipecs_wss_base (self) -> str:
        return self._config['ipecs']['BaseWSS']
    @property
    def ipecs_wss_full (self) -> str:
        return self._config['ipecs']['FullWSS']
    @property
    def ipecs_port (self) -> int:
        return self._config['ipecs']['Port']
    @property
    def ipecs_type (self) -> str:
        return self._config['ipecs']['type']
    @property
    def ipecs_target (self) -> str:
        return self._config['ipecs']['target']
    @property
    def ipecs_api_version (self) -> str:
        return self._config['ipecs']['APIVersion']
    @property
    def ipecs_verify (self) -> bool:
        return self._config['ipecs']['verify']
    @property
    def ipecs_disable_SSL_warnings (self) -> bool:
        return self._config['ipecs']['disableSSLWarnings']
    @property
    def ipecs_retry_attempts (self) -> int:
        return self._config['ipecs']['retry-attempts']
    @property
    def ipecs_retry_rate (self) -> int:
        return self._config['ipecs']['retry-rate']
    @property
    def ipecs_timeout (self) -> int:
        return self._config['ipecs']['timeout']
    @property
    def ipecs_socket_timeout (self) -> int:
        return self._config['ipecs']['socket-timeout']
    @property
    def ipecs_ping_timeout (self) -> int:
        return self._config['ipecs']['ping-timeout']
    @property
    def socket_ping_interval (self) -> int:
        return self._config['ipecs']['socket-ping-interval']
    @socket_ping_interval.setter
    def socket_ping_interval (self, value) -> None:
        self._config['ipecs']['socket-ping-interval'] = value
        self._hasChanges = True
    @property
    def ipecs_server_ip (self) -> str:
        return self._srvIP
    @property
    def ipecs_base_uri (self) -> str:
        return self._baseURI
    @property
    def ipecs_full_uri (self) -> str:
        return self._fullURI
    @property
    def ipecs_ip (self) -> str:
        return self._srvIP
    @property
    def ipecs_metrics_reset_time (self) -> str:
        return self._config['ipecs']['metrics-reset-time']
    @property
    def ipecs_metrics_reset_enabled (self) -> bool:
        return self._config['ipecs']['metrics-reset-enabled']
    def ipecs_set_ip (self, address) -> None:
        self._config['ipecs']['last-know-ip'] = address
        self._hasChanges = True
    @property
    def ipecs_fail_on_event_malformat (self) -> bool:
        return self._config['ipecs']['fail-on-event-data-malformat']
    @property
    def ipecs_event_date_format (self) -> str:
        return self._event_time_format
    @property
    def ipecs_keep_alive_timeout (self) -> int:
        return self._config['ipecs']['keepAliveTimer']
    @property
    def ipecs_max_socket_retries (self) -> int:
        return self._config['ipecs']['max-socket-retries']
    @property
    def ipecs_max_missed_pings (self) -> int:
        return self._config['ipecs']['max-missed-pings']
    @property
    def ipecs_log_all_events (self) -> bool:
        return self._config['ipecs']['log-all-events']
    @property
    def ipecs_stations (self) -> list:
        return self._config['ipecs']['stations']
    @property
    def ipecs_queues (self) -> list:
        return self._config['ipecs']['queues']
    @property
    def ipecs_status_data_calls_only (self) -> bool:
        return self._config['ipecs']['status-calls-only']
    @property
    def ipecs_supported_events (self) -> list:
        return self._config['ipecs']['events-allowed']
    @ipecs_supported_events.setter
    def ipecs_supported_events (self, value: list) -> None:
        self._config['ipecs']['events-allowed'] = value
        self._hasChanges = True
    @property
    def ipecs_blocked_events (self) -> list:
        return self._config['ipecs']['events-blocked']
    @ipecs_blocked_events.setter
    def ipecs_blocked_events (self, value: list) -> None:
        self._config['ipecs']['events-blocked'] = value
        self._hasChanges = True
    @property
    def enable_troubleshooting (self) -> bool:
        return self._config['ipecs']['troubleshoot']
    def ipecsSaveSessionToken (self, token: str) -> None:
        if token is not None:
            self._saveSessionToken (token)
        return
    def ipecsGetSessionToken (self) -> dict:
        return self._getSessionToken ()
# Mongo related properties
    @property
    def mongo_url (self) -> str:
        return self._config['mongo']['url']
    @property
    def mongo_port (self) -> int:
        return self._config['mongo']['port']
    @property
    def mongo_connectTimeoutMS (self) -> int:
        return self._config['mongo']['connectTimeoutMS']
    @property
    def mongo_socketTimeoutMS (self) -> int:
        return self._config['mongo']['socketTimeoutMS']
    @property
    def mongo_db_name (self) -> str:
        return self._config['mongo']['db-name']
    @property
    def mongo_col_call_events (self) -> str:
        return self._config['mongo']['collections']['call-events']
    @property
    def mongo_col_call_history (self) -> str:
        return self._config['mongo']['collections']['call-history']
    @property
    def mongo_col_call_summary (self) -> str:
        return self._config['mongo']['collections']['call-summary']
    @property
    def mongo_col_agent_events (self) -> str:
        return self._config['mongo']['collections']['agent-events']
    @property
    def mongo_col_agent_history (self) -> str:
        return self._config['mongo']['collections']['agent-history']
    @property
    def mongo_col_agent_summary (self) -> str:
        return self._config['mongo']['collections']['agent-summary']
    @property
    def mongo_col_user_types (self) -> str:
        return self._config['mongo']['collections']['user-types']
    @property
    def mongo_col_users (self) -> str:
        return self._config['mongo']['collections']['users']
    @property
    def mongo_col_phone_extensions (self) -> str:
        return self._config['mongo']['collections']['phone-extensions']
    @property
    def mongo_replaceRecords (self) -> bool:
        return self._config['mongo']['replaceRecords']
    @property
    def mongo_updateRecords (self) -> bool:
        return self._config['mongo']['updateRecords']
    @property
    def mongo_db_secured (self) -> bool:
        return self._config['mongo']['db-secured']
    @property
    def mongo_retry_attempts (self) -> int:
        return self._config['mongo']['retry-attempts']
    @property
    def mongo_retry_rate (self) -> int:
        return self._config['mongo']['retry-rate']
    @property
    def mongo_date_format (self) -> str:
        return self._config['mongo']['dateformat']
    @property
    def event_simulation (self) -> bool:
        return self._config['mongo']['simulate']
# Resource related properties
    @property
    def resource_file (self) -> str:
        return self._config['resource']['resource-file']
    @property
    def key_file (self) -> str:
        return self._config['resource']['key-file']
    @property
    def command_file (self) -> str:
        return self._config['resource']['commands-file']
    @property
    def pem_file (self) -> str:
        return self._config['resource']['pem-file']
    @property
    def log_file (self) -> str:
        return self._config['resource']['log-file']
    @property
    def log_file_name (self) -> str:
        return os.path.join (os.getcwd(), self.log_path, self.log_file)
    @property
    def log_path (self) -> str:
        return self._config['resource']['log-path']
# Logging related properties
    @property
    def Logger (self):
        return self._log
    @property
    def log_to_file (self) -> bool:
        return self._config['log']['log-to-file']
    @property
    def log_to_stdout (self) -> bool:
        return self._config['log']['log-to-stdout']
    @property
    def log_socket_errors (self) -> bool:
        return self._config['log']['log-socket-errors']
    @property
    def log_file_max_size (self) -> int:
        return self._config['log']['max_bytes']
    @property
    def log_file_count (self) -> int:
        return self._config['log']['max_bytes']
    @property
    def log_file_truncate (self) -> bool:
        return self._config['log']['truncate']
    @property
    def log_file_rotate (self) -> bool:
        return self._config['log']['rotate']
    @property
    def log_level (self) -> str:
        return self._config['log']['level']
    @property
    def log_verbose (self) -> bool:
        return self._config['log']['verbose']
    @property
    def log_format_debug (self) -> str:
        return self._config['log']['format-debug']
    @property
    def log_format (self) -> str:
        return self._config['log']['format']
    @property
    def log_date_format (self) -> str:
        return self._config['log']['dateformat']
    @property
    def log_ts_format (self) -> str:
        return self._config['log']['ts_format']
    def log_event (self, event, level):
        print ('log_event Not yet implemented.')
    def log_raw_events (self) -> bool:
        return self._config['ipecs']['log-raw-events']
# Security related properties
    @property
    def ipecs_uid (self):
        return self._get_user_id ('ipecs')
    @ipecs_uid.setter
    def ipecs_uid (self, value):
        self._set_user_id (value, 'ipecs')
    @property
    def ipecs_uid_len (self) -> int:
        return len (self._config['ipecs']['uid'])
    @property
    def mongo_uid (self):
        return self._get_user_id ('mongo')
    @mongo_uid.setter
    def mongo_uid (self, value):
        self._set_user_id (value, 'mongo')
    @property
    def mongo_uid_len (self) -> int:
        return len (self._config['mongo']['uid'])

    def _get_user_id (self, section: str) -> str:
        try:
            self._ary_keys_cnf.index (section)
            #if self.uid_secure (section):
            #    return self._cipher.decrypt (ciphertext=bytes (self._config[section]['uid'], 'utf-8'))
            #else:
            #self._log.warning (self._resources['cipher']['wrn001'])
            return self._config[section]['uid']
        except ValueError:
            raise KeyError (self._resources['err']['err002'].format (section, 'ipecs.conf'))

    def _set_user_id (self, uid: str, section: str):
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        try:
            self._ary_keys_cnf.index (section)
            self._config[section]['uid'] = uid
            #if uid != self._config[section]['uid']:
            #    self._config[section]['uid'] = str (self._cipher.encrypt (message=uid), 'utf-8')
            #    self._config[section]['uid-secure'] = True
            #    self._hasChanges = True
            #    return
            #else:
            #    self._log.warning (self._resources['cipher']['wrn002'])
        except ValueError:
            raise KeyError (self._resources['err']['err002'].format (section, 'ipecs.conf'))
        except Exception as ex:
            raise (ex)

    @property
    def ipecs_password (self):
        return self._get_password ('ipecs')
    @ipecs_password.setter
    def ipecs_password  (self, value):
        self._set_password (pw=value, section='ipecs')
    @property
    def ipecs_pw_len (self) -> int:
        return len (self._config['ipecs']['pw'])
    @property
    def mongo_password (self):
        return self._get_password ('mongo')
    @mongo_password.setter
    def mongo_password  (self, value):
        self._set_password (pw=value, section='mongo')
    @property
    def mongo_pw_len (self) -> int:
        return len (self._config['mongo']['pw'])


    def _get_password (self, section: str) -> str:
        try:
            self._ary_keys_cnf.index (section)
            return self._config[section]['pw']
            #if self._config[section]['pw-secure']:
            #    return self._cipher.decrypt (ciphertext=bytes (self._config[section]['pw'], 'utf-8'))
            #else:
            #    return self._config[section]['pw']
        except ValueError:
            raise KeyError (self._resources['err']['err002'].format (section, 'ipecs.conf'))

    def _set_password (self, pw: str, section: str):
        try:
            self._ary_keys_cnf.index (section)
            self._config[section]['pw'] = pw
            #if pw != self._config[section]['pw']:
            #    self._config[section]['pw'] = str (self._cipher.encrypt (message=pw), 'utf-8')
            #    self._config[section]['pw-secure'] = True
            #    self._hasChanges = True
            #else:
            #    self._log.warning (self._resources['cipher']['wrn003'])
        except ValueError:
            raise KeyError (self._resources['err']['err002'].format (section, 'ipecs.conf'))

    def uid_secure (self, section: str) -> bool:
        try:
            self._ary_keys_cnf.index (section)
            return self._config[section]['uid-secure']
        except ValueError:
            raise KeyError (self._resources['err']['err002'].format (section, 'ipecs.conf'))
    
    def password_secure (self, section: str) -> bool:
        try:
            self._ary_keys_cnf.index (section)
            return self._config[section]['pw-secure']
        except ValueError:
            raise KeyError (self._resources['err']['err002'].format (section, 'ipecs.conf'))

    def encryptLoginDetails (self, section: dict):
        try:
            return
            #if not self._config['options']['force-security']:
            #    return
            #if not self._config['options']['random-str'] > 0:
            #    self._config['options']['random-str'] = self._cipher.createIV ()
            #    self._hasChanges = True
            #if not self._config[section]['pw-secure']:
            #    self._log.warning (self._resources['cipher']['enc003'].format(self._resources['cipher']['msg001'], section))
            #    # Encrypt and overwrite the existing password in the config file
            #    self._config[section]['pw'] = str (self._cipher.encrypt (message=self._config[section]['pw']), 'utf-8')
            #    self._config[section]['pw-secure'] = True
            #    self._hasChanges = True
            #    # loop back test
            #    #print (self._cipher.decrypt (ciphertext=bytes (self._config[section]['pw'], 'utf-8')))
            #if not self._config[section]['uid-secure']:
            #    self._log.warning (self._resources['cipher']['enc003'].format(self._resources['cipher']['msg002'], section))
            #    # Encrypt and overwrite the existing password in the config file
            #    self._config[section]['uid'] = str (self._cipher.encrypt (message=self._config[section]['uid']), 'utf-8')
            #    self._config[section]['uid-secure'] = True
            #    self._hasChanges = True
            #    # loop back test
            #    #print (self._cipher.decrypt (ciphertext=bytes (self._config[section]['uid'], 'utf-8')))
            #if self._hasChanges:
            #    self.saveConfiguration ()
        except Exception as ex:
            raise (ex)
# Option related properties
    @property
    def backup_count (self) -> int:
        return self._config['options']['backup-count']
    @property
    def encrypt_backup (self) -> int:
        return self._config['options']['encrypt-backup']
    @property
    def force_save (self) -> int:
        return self._config['options']['force-save']
    @property
    def use_test_cases (self) -> bool:
        return self._config['options']['use-test-cases']

class iPECsLoggingHandler (StreamHandler):
    def __init__(self, handler):
        StreamHandler.__init__(self)
        self._handler = handler
    def emit (self, record):
       self._handler (self.format (record))
