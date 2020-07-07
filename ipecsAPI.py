# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import  json
import  os, ssl
import  sys
import  time
import  socket
import  requests
import  urllib3
from    requests.auth import HTTPBasicAuth
import  logging
from    logging.handlers import RotatingFileHandler
from    __version import __version__
from    __version import __product__

class ipecsAPI:
    __notInitErr = "iPECsAPI ->> class ipecsAPI has not been initialised properly!"
    __cnf = {}
    __res = {}
    __cmds = {}
    __ipecs = {}
    __hdrs = {}
    __rsps = {}
    __ops  = {}
    __baseURI = ''
    __fullURI = ''
    __wssURI  = ''
    __srvIP   = ''
    __sessiontoken = ''
    __log = logging.Logger
    __isLoggedIn = False
    __isInitialised = False
    __hasServerIP = False

# Initialise
    """
    Function __init__ initialises ipecsAPI class.
    
    Parameters
    ----------
    f_name : the fqdn of the iPECsAPI configuration file, default is ipecs.conf
    log_id : the name that will precede log entries in the log file and console log.

    The function will raise an exception if anything goes wrong.
    """
    def __init__ (self, f_name='ipecs.conf', log_id='iPECsAPI') -> None:
        self.__f_log = ''
        self.__f_name = f_name
        # Load json configuration file
        try:
            # Make sure firl exists
            if os.path.exists(f_name) == False:
                logging.fatal(f"iPECsAPI ->> Can't find input file {f_name}. Execution cannot continue!")
                # File does not exist, cannot continue - bail out
                raise FileNotFoundError (f_name)
            else:
                # All good, read file
                with open (f_name, 'r') as json_file:
                    data = json_file.read()
                # Parse file data    
                self.__cnf = json.loads(data)
            # Try to configure logging function
            self.__log = self.config_logger (log_id)
            self.loadResourceFile ()
            self.loadCommandsFile ()
            # Make sure to avoid SSl errors
            if self.__cnf['URI']['disableSSLWarnings']:
                if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
                    self.__log.info (self.__res['inf']['inf003'])
                    ssl._create_default_https_context = ssl._create_unverified_context
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.getBaseURI ()
            self.getFullURI ()
            self.getiPECsServerIP ()
            self.getbaseWSS ()
            # Initialisation complete - we can use his class now
            self.__isInitialised = True
        except KeyError as err:
            self.__log.fatal (err, exc_info=True)
            raise Exception (err)
        except ValueError as v_err:
            self.__log.fatal (v_err)
            raise Exception (err)
        except FileNotFoundError as fnf_err:
            self.__log.fatal (fnf_err, exc_info=True)
            raise Exception (err)
        except PermissionError as p_err:
            self.__log.error (p_err, exc_info=True)
            raise Exception (err)
        except OSError as e:
            self.__log.error (e, exc_info=True)
            raise Exception (err)
        except Exception as e:
            self.__log.fatal (e, exc_info=False)
            raise Exception (err)

# Configure Logger
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
        try:
            truncated = False
            f_log = os.path.join (os.getcwd(), self.__cnf['log']['log-path'], self.__cnf['log']['log-file'])
            cwd = os.getcwd()
            log_path = os.path.join (cwd, self.__cnf['log']['log-path'])
            if os.path.exists (log_path) == False:
                os.makedirs (log_path, mode=0o766, exist_ok=True)
            # Check if log-file exists
            if os.path.exists(f_log) == False:
                os.chdir (log_path)
                fp = open (f_log, "w+")
                os.chmod (f_log, mode=0o766)
                os.chdir (cwd)
                fp.close()
            else:
                # Check file size and truncate if required
                f_size = os.path.getsize(f_log)
                if (f_size > self.__cnf['log']['max_bytes'] and self.__cnf['log']['truncate'] and not self.__cnf['log']['rotate']):
                    # truncate the file
                    fp = open (f_log, 'w')
                    truncated = True
                    fp.close()

            # Setup formatter for logging system
            # Enable logging to file
            if (self.__cnf['log']['log-to-file']):
                logger = logging.getLogger(id)
                logger.setLevel(self.__cnf['log']['level'])
                if (self.__cnf['log']['rotate']):
                    file_handler = RotatingFileHandler(f_log, maxBytes=self.__cnf['log']['max_bytes'], backupCount=self.__cnf['log']['backup_count'])
                else:
                    file_handler = logging.FileHandler(f_log)
                logger.addHandler(file_handler)
                if (self.__cnf['log']['level'] == "DEBUG"):
                    formatter = logging.Formatter (fmt=self.__cnf['log']['format-debug'], datefmt=self.__cnf['log']['dateformat'])
                else:
                    formatter = logging.Formatter (fmt=self.__cnf['log']['format'], datefmt=self.__cnf['log']['dateformat'])
                file_handler.setFormatter (formatter)
            else:
                if (self.__cnf['log']['level'] == "DEBUG"):
                    logging.basicConfig(level=self.__cnf['log']['level'], format=self.__cnf['log']['format-debug'], datefmt=self.__cnf['log']['dateformat'])
                else:
                    logging.basicConfig(level=self.__cnf['log']['level'], format=self.__cnf['log']['format'], datefmt=self.__cnf['log']['dateformat'])
            # Enable logging to stdout - this works as if log-to-file is true, and log-to-stdout is true add another logger to stdout
            # if log-to-file is false, then enforce stdout logger regardless of log-to-stdout flag
            if (self.__cnf['log']['log-to-stdout'] or not self.__cnf['log']['log-to-file']):
                logger = logging.getLogger(id)
                consoleHandler = logging.StreamHandler()
                consoleHandler.setLevel(self.__cnf['log']['level'])
                logger.addHandler(consoleHandler)
                if (self.__cnf['log']['level'] == "DEBUG"):
                    formatter = logging.Formatter(fmt=self.__cnf['log']['format-debug'], datefmt=self.__cnf['log']['dateformat'])
                else:
                    formatter = logging.Formatter(fmt=self.__cnf['log']['format'], datefmt=self.__cnf['log']['dateformat'])
                consoleHandler.setFormatter(formatter)
            version = '.'.join(str(c) for c in __version__)
            logger.info (str.format("{} version {} loaded.", __product__, version))
            logger.debug ("Log system activated.")
            if (truncated):
                logger.warning (f'Log-file has been truncated! - Previous log-entries lost!')
            del f_log
            return logger
        except FileExistsError as ex:
            logging.fatal ("iPECsAPI -> File does not error.")
        except PermissionError as ex:
            logging.fatal ("iPECsAPI -> File permission error.")
        except Exception as ex:
            raise (ex)

# Load Resource File
    """
    Function loadResourceFile() -> None.
    
    Parameters
    ----------
    none : nil.

    The function loads the language resource file defined in the configuration file specified in the __init__ function.
    """
    def loadResourceFile (self) -> None:
        try:
            f_res = os.path.join (os.getcwd(), self.__cnf['resource']['resource-file'])
            # Check if resource-file exists
            if os.path.exists(f_res) == False:
                raise FileNotFoundError ("The language resource file {f_res} could not be found. Execution halted!")
            with open (f_res, 'r') as json_file:
                data = json_file.read()
            # Parse file data    
            self.__res = json.loads(data)
            self.__log.info (self.__res['msg']['msg001'].format (f_res))
            del f_res

        except PermissionError as ex:
            logging.fatal ("iPECsAPI -> File {f_res} permission error.")
        except Exception as ex:
            raise (ex)

# Load iPECs Commands and Headers File
    """
    Function loadCommandsFile() -> None.
    
    Parameters
    ----------
    none : nil.

    The function loads the language resource file defined in the configuration file specified in the __init__ function.
    """
    def loadCommandsFile (self) -> None:
        try:
            f_cmd = os.path.join (os.getcwd(), self.__cnf['resource']['commands-file'])
            # Check if resource-file exists
            if os.path.exists(f_cmd) == False:
                raise FileNotFoundError (self.__res['err']['err003'].format(f_cmd))
            with open (f_cmd, 'r') as json_file:
                data = json_file.read()
            # Parse file data
            self.__ipecs = json.loads(data)
            self.__cmds = self.__ipecs['commands']
            self.__hdrs = self.__ipecs['headers']
            self.__rsps = self.__ipecs['responses']
            self.__ops  = self.__ipecs['op-codes']
            self.__log.info (self.__res['msg']['msg002'].format (f_cmd))
            del f_cmd

        except PermissionError as ex:
            logging.fatal ("iPECsAPI -> File {f_cmd} permission error.")
        except Exception as ex:
            raise (ex)

# Get Base URI from Config File
    """
    Function getBaseURI() -> string.
    
    Parameters
    ----------
    none : nil.

    The function generates, stores locally and returns the base URI pointing the the iPECs API server.
    The parameters are defined in the configuration file specified in the __init__ function.
    """
    def getBaseURI (self) -> str:
        self.__baseURI = "{}:{}/{}/".format(self.__cnf['URI']['BaseURI'],self.__cnf['URI']['Port'],self.__cnf['URI']['type'])
        self.__log.debug ((self.__res['dbg']['dbg001']).format (self.__baseURI))
        return (self.__baseURI)

# Get Full URI from Config File
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
            self.__fullURI = "{}{}/{}/users/".format(self.getBaseURI(), self.__cnf['URI']['target'], self.__cnf['URI']['APIVersion'])
        else:
            self.__fullURI = "{}{}/users/".format(self.getBaseURI(), self.__cnf['URI']['APIVersion'])
        self.__log.debug ((self.__res['dbg']['dbg002']).format (self.__fullURI))
        return (self.__fullURI)

# Get base WSS (secure socket address)
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
            if not self.__hasServerIP:
                self.getiPECsServerIP
            self.__wssURI = self.__cnf['URI']['BaseWSS'].format (self.__srvIP, self.__cnf['URI']['Port'])
            self.__log.debug(self.__res['dbg']['dbg004'].format(self.__wssURI))
            return self.__wssURI
        except Exception as ex:
            raise (ex) 

# Provide logging pointer
    """
    Function getlogger() -> dictionary.
    
    Parameters
    ----------
    section :   <str> specifies the sub-section of the dictionary to return.
                default is to return all sections.

    The function returns a fully formatted and configured object of type <logging.Logger> to be used to log events.
    """
    def getlogger (self):
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        return self.__log

# Provide pointer to language resource file
    """
    Function getResources() -> dictionary.
    
    Parameters
    ----------
    section :   <str> specifies the sub-section of the dictionary to return.
                default is to return all sections.

    The function returns an object of type {dict} containing the language strings.
    """
    def getResources (self, section=None) -> dict:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        if section is None:
            return self.__res
        for key in self.__res.items():
            if key[0] == section:
                return self.__res[section]
        raise KeyError (self.__res['err']['err002'].format(section))

# Provide pointer to configuration file
    """
    Function getConfiguration() -> dictionary.
    
    Parameters
    ----------
    section :   <str> specifies the sub-section of the dictionary to return.
                default is to return all sections.

    The function returns an object of type {dict} containing the configuration settings.
    """
    def getConfiguration (self, section=None) -> dict:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        if section is None:
            return self.__cnf
        for key in self.__cnf.items():
            if key[0] == section:
                return self.__cnf[section]
        raise KeyError (self.__cnf['err']['err002'].format(section))

# Provide pointer to ipecs commands
    """
    Function getCommands() -> dictionary.
    
    Parameters
    ----------
    none : nil.

    The function returns an object of type {dict} containing the iPECs commands.
    """
    def getCommands (self) -> dict:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        return self.__cmds

# Provide pointer to ipecs headers
    """
    Function getHeaders.
    
    Parameters
    ----------
    none : nil.

    The function returns an object of type {json} containing the iPECs http header strings needed for command execution.
    """
    def getHeaders (self) -> dict:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        return self.__hdrs

# Provide pointer to ipecs responses
    """
    Function getResponses.
    
    Parameters
    ----------
    none : nil.

    The function returns an object of type {json} containing the iPECs http response types generated by command execution.
    """
    def getResponses (self) -> dict:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        return self.__hdrs

# Provide pointer to ipecs op-codes
    """
    Function getOpCodes.
    
    Parameters
    ----------
    none : nil.

    The function returns an object of type {json} containing the iPECs command operation codes.
    """
    def getOpCodes (self) -> dict:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        return self.__ops

# Provide pointer to iPECs command related info
    """
    Function getiPECsCommands() -> dictionary.
    
    Parameters
    ----------
    section :   <str> specifies the sub-section of the dictionary to return.
                default is to return all sections.

    The function returns an object of type {dict} containing the language strings.
    """
    def getiPECsCommands (self, section=None) -> dict:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        if section is None:
            return self.__ipecs
        for key in self.__ipecs.items():
            if key[0] == section:
                return self.__ipecs[section]
        raise KeyError (self.__res['err']['err002'].format(section))

# Get IP address of ipecs server
    """
    Function getiPECsServerIP.
    
    Parameters
    ----------
    none : nil.

    The function returns the IP address of the iPECs API server specified in the configuration file.
    Function will throw an exception if an error occurs.
    """
    def getiPECsServerIP (self):
        try:
            if self.__cnf['URI']['BaseURI'].startswith('https://'):
                host = self.__cnf['URI']['BaseURI'].replace('https://', '')
            else:
                host = self.__cnf['URI']['BaseURI']
            self.__srvIP = socket.gethostbyname (host)
            self.__log.info (self.__res['inf']['inf001'].format (host, self.__srvIP))
            self.__hasServerIP = True
            return self.__srvIP
        except socket.error as ex:
            self.__hasServerIP = False
            raise ConnectionError (self.__res['err']['err001'].format (host, ex))
        finally:
            del host

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
    def isUserLoggedIn (self):
        return self.__isLoggedIn

# Helper function to check HTTP response for errors
    """
    Function __httpCheckResponse checks the HTTP response received from a http request sent.
    It will log the error details in the logger and then throw an exception of type <requests.exceptions.HTTPError>
    if there are errors. It will return with None if all is clear.
    
    Parameters
    ----------
    none : nil.

    Returns:
    ----------
    None:    
    """
    def __httpCheckResponse (self, response, command):
        err = ''
        # Server error
        if response.status_code >= 500:
            err = self.__res['http']['500'].format(response.status_code)
            self.__log.error(err)
            raise requests.exceptions.HTTPError (err)
        # URL not found
        elif response.status_code == 404:
            err = self.__res['http']['404'].format(response.status_code, command)
            self.__log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # Operation forbidden
        elif response.status_code == 403:
            err = self.__res['http']['403'].format(response.status_code, command)
            self.__log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # Authentication Failed or Access not authorised
        elif response.status_code == 401:
            err = self.__res['http']['401'].format(response.status_code)
            self.__log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # Bad Request
        elif response.status_code == 400:
            err = self.__res['http']['400'].format(response.status_code)
            self.__log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # Unexpected Redirect
        elif response.status_code >= 300:
            err = self.__res['http']['300'].format(response.status_code)
            self.__log.error (err)
            raise requests.exceptions.HTTPError (err) 
        # All good to go
        elif response.status_code == 200:
            self.__log.info (self.__res['http']['200'].format(command))
            return
        else:
            # Unexpected Error
            err = self.__res['http']['100'].format(response.status_code, response.content)
            self.__log.error (err)
            raise requests.exceptions.HTTPError (err) 

# Helper function to log error message received from iPECs API
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
            msg = self.__res['ipecs']['error'].format(json['error']['code'], json['error']['message'])
            self.__log.error (msg)
        except KeyError as ex:
            self.__log.error (self.__res['err']['err002'].format(ex))
            raise KeyError (ex)

# Function filters, prepares parameters and sends command to be send to iPECs API to appropriate command function
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

    def sendCommand (self, command, opcode=None, user=None, pw=None, arg1=None, arg2=None, arg3=None, arg4=None) -> json:
        # The class is not properly initialised, cannot function - raise exception
        if not self.__isInitialised:
            raise RuntimeError (self.__cnf['ipecs']['err002'].format(command, self.__cnf['resource']['commands-file'], "commands"))
        if not self.__isLoggedIn and command != 'login':
            raise UserWarning (self.__cnf['http']['http003'])
        
        found = False
        # Check if the desired command is listed in the supported commands list
        for key in self.__cmds:
            if key == command:
                found = True
                break
        if not found:
            self.__log.error (self.__res['ipecs']['err002'].format(command, self.__cnf['resource']['commands-file'], "commands"))
            raise NotImplementedError (self.__res['ipecs']['err003'].format(command))
        try:
            self.__log.debug (self.__res['dbg']['dbg003'].format (command))
            if command == 'login': 
                self.login (user=user, pw=pw)
                return None
            elif command == 'logout': 
                self.logout (user=user)
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
                return self.__smdr (user, params)
            else:
                raise NotImplementedError (self.__res['ipecs']['wrn001'].format(command))
        except Exception as ex:
            raise ex

# Send login command to iPECs Server API
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
    def login (self, user, pw) -> bool:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        if self.__isLoggedIn or user is None:
            self.__log.debug (self.__res['http']['http001'].format(user))
            return
        try:
            cmd = self.__cmds['login'].format(self.__fullURI, user)
            self.__log.debug (self.__res['inf']['inf002'].format(cmd))
            try:
                retries = self.__cnf['URI']['login-retries']
                if retries <= 0: retries = 1
                for i in range (0, retries, 1):
                    response = requests.get(cmd, auth=HTTPBasicAuth(user, pw), headers=self.__cnf['header'], verify=self.__cnf['URI']['verify'])
                    if response.status_code == 401:
                        if retries > 1:
                            self.__log.debug(self.__res['dbg']['dbg005'].format(self.__cnf['URI']['retry-delay']))
                            time.sleep (self.__cnf['URI']['retry-delay'])
                            if i == self.__cnf['URI']['login-retries'] - 1:
                                self.__log.critical (self.__res['dbg']['dbg006'].format(self.__cnf['URI']['login-retries']))
                                raise requests.exceptions.HTTPError (self.__res['http']['401'].format(response.status_code)) 
                    else:
                        self.__httpCheckResponse (response, cmd)
                        self.__rsps['rsp_login'] = response.json()
                        self.__sessiontoken = self.__rsps['rsp_login']['token']             
                        self.__isLoggedIn = True
                        break
            except urllib3.exceptions.InsecureRequestWarning as ex:
                self.__log.error (ex)
            except requests.exceptions.SSLError as ex:
                self.__log.error (ex)
        except KeyError as ex:
            self.__log.error (self.__res['err']['err002'].format (ex))
        except Exception as ex:
            self.__log.fatal (ex)
        finally:
            return self.__isLoggedIn

# Send logout command to iPECs Server API
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
    def logout (self, user='admin') -> bool:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        if not self.__isLoggedIn or user is None:
            self.__log.debug (self.__res['http']['http002'].format(user))
            return
        try:
            cmd = self.__cmds['logout'].format(self.__fullURI, user)
            self.__log.debug (self.__res['inf']['inf002'].format(cmd))
            try:
                hed = {}
                hed['Authorization'] = 'Bearer ' + self.__sessiontoken
                response = requests.post(cmd, headers=hed, verify=self.__cnf['URI']['verify'])
                self.__httpCheckResponse (response, cmd)
                self.__isLoggedIn = False
            except urllib3.exceptions.InsecureRequestWarning as ex:
                self.__log.error (ex)
            except requests.exceptions.SSLError as ex:
                self.__log.error (ex)
            finally:
                del hed
        except KeyError as ex:
            self.__log.error (self.__res['err']['err002'].format (ex))
        except Exception as ex:
            self.__log.critical (ex)
        finally:
            del cmd
            return not self.__isLoggedIn
    
# Send SMDR command to iPECs Server API
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
    def __smdr (self, user=None, params=None) -> dict:
        if not self.__isInitialised:
            raise RuntimeError (self.__notInitErr)
        if not self.__isLoggedIn or user is None:
            self.__log.debug (self.__res['http']['http002'].format(user))
            return
        try:
            cmd = self.__cmds['smdr'].format(self.__fullURI, user)
            self.__log.debug (self.__res['inf']['inf002'].format(cmd))
            # self.__log.debug ("Request Header: {}".format(self.__cnf['header']))
            try:
                response = requests.get (cmd, headers='Bearer ' + self.__sessiontoken, params=params, verify=self.__cnf['URI']['verify'])
                self.__httpCheckResponse (response, cmd)
                json = response.json()
                return json
            except urllib3.exceptions.InsecureRequestWarning as ex:
                self.__log.error (ex)
            except requests.exceptions.SSLError as ex:
                self.__log.error (ex)
        except KeyError as ex:
            self.__log.error (self.__res['err']['err002'].format (ex))
        except Exception as ex:
            self.__log.fatal (ex)
