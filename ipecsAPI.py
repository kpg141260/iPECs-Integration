import json
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from __version import __version__
from __version import __product__

class ipecsAPI:
    __cnf = {}
    __res = {}
    __baseURI = ""
    __fullURI = ""
    __log = logging.Logger
    __isInitialised = False

# Initialise
    def __init__ (self, f_name='ipecs.conf', log_id='iPECsAPI'):
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
            self.__isInitialised = True
        except Exception as ex:
            raise (ex)


# Configure Logger
    def config_logger (self, id):
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
    def loadResourceFile (self):
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

# Get Base URI from Config File
    def getBaseURI (self):
        if not self.__isInitialised:
            raise RuntimeError ("iPECsAPI ->> class ipecsAPI has not been initialised properly!")
        
        self.__baseURI = "{}:{}/{}/".format(self.__cnf['URI']['BaseURI'],self.__cnf['URI']['Port'],self.__cnf['URI']['type'])
        self.__log.debug ((self.__res['dbg']['dbg001']).format (self.__baseURI))
        return (self.__baseURI)

# Get Full URI from Config File
    def getFullURI (self):
        if not self.__isInitialised:
            raise RuntimeError ("iPECsAPI ->> class ipecsAPI has not been initialised properly!")
        
        self.__fullURI = "{}{}/users/{}/".format(self.getBaseURI(), self.__cnf['URI']['APIVersion'],self.__cnf['URI']['UID'])
        self.__log.debug ((self.__res['dbg']['dbg002']).format (self.__fullURI))
        return (self.__fullURI)

# Provide logging pointer
    def getlogger (self):
        return self.__log
    
