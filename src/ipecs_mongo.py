# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import  logging
import  threading, time
import  asyncio, subprocess
import  uuid

from datetime   import datetime
from pymongo    import cursor
from pymongo    import MongoClient
from pymongo    import errors as mdb_errors

LOGGING_ID      = 'iPECsAPI'
_isConnected    = False
mongo_loop      = asyncio.new_event_loop ()
mongo_client    = MongoClient()
resources:      dict
config:         dict
verbose_mode:   bool
logger:         logging.Logger

class ipecs_db_io:
    def __init__ (self, res:dict, conf:dict, verbose: bool=False):
        """
        Initialises the ipecs_dbio class.
        
        Parameters
        ----------
        env: dictionary - contains the environment parameters
        cnf: dictionary - contains configuration parameters
        """
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode
        try:
            logger         = logging.getLogger (LOGGING_ID)
            config         = conf
            resources      = res
            verbose_mode   = verbose
            self._cnt_iv   = 0
            self.dbConnect ()
            logger.debug (resources['db020'].format(self.__class__))
            self._id_fmt   = config['id-date-format']
        except Exception as e:
            raise Exception (e)

    def __del__ (self):
        global mongo_client
        global resources
        global config
        global logger

        if self._thread_mongo_status.isAlive():
            self._thread_mongo_status.kill()
            #self._thread_mongo_status.join()
        mongo_client.close()
        del mongo_client
        del config
        del logger
        del resources

    def shutdown (self):
        if logger is not None:
            logger.info (resources['db022'])
        self.__del__()

    def dbCheckConnectionStatus (self):
        """
        Checks the connection to a Mongo database.
        
        Parameters
        ----------
        db: object - MongoDB database connection object

        Returns
        ---------
        int:  1 for connection is live and database can accept commands
             -1 if database is not responsive
        """
        global mongo_client
        global resources
        global config
        global logger

        con_stat = mongo_client.admin.command ('ping')
        if con_stat ['ok'] != 1.0:
            return 0
        else:
            return 1

    @property
    def mongo_connected (self) -> bool:
        global _isConnected
        return _isConnected

    def dbConnect (self, url=None, port=None, current_retry=0) -> None:
        """
        Attempts to connect to a MongoDB server.
        
        Parameters
        ----------
        url: string connection string such as 'mongodb://10.10.10.10
        port: int the port to connect to, such as '27017'

        Returns
        ---------
        object: Mongo client
        """
        global mongo_client
        global _isConnected
        global resources
        global config
        global logger

        if url is None:
            url = config['url']
        if port is None:
            port = config['port']
        _current_attempt = current_retry
        try:
            logger.info (str.format(resources['db001'], url, port, config['connectTimeoutMS'], config['socketTimeoutMS']))
            mongo_client = MongoClient (url, port, connectTimeoutMS=config['connectTimeoutMS'], socketTimeoutMS=config['socketTimeoutMS'])
            try:
                # mongo_client.server_info ()
                self._thread_mongo_status = ipecs_db_io.iPECsMongoThread (threadID=100, interval=config['connectionCheckTimeoutMS'])
                self._thread_mongo_status.daemon = True
                self._thread_mongo_status.start()
                _isConnected = True
            # Mongo server is not responding
            except Exception:
                # check if the thread is alive and if yes, kill it
                if self._thread_mongo_status.is_alive():
                    self._thread_mongo_status.kill()
                    self._thread_mongo_status.join()
                logger.warning (resources['db019'].format(url), config['retry-rate'], _current_attempt + 1)
                if _current_attempt < config['retry-attempts']:
                    time.sleep (config['retry-rate'])
                    self.dbConnect (url=url, port=port, current_retry=_current_attempt + 1)
                else:
                    raise Exception (str.format (resources['db003'], url, port))
        except Exception as ex:
            raise (ex)
        # We are connected
        logger.info (str.format(resources['db006'], url, port))

# ================== Register new call event to MongoDB -- THREAD SAFE -- ===============
    def _make_id (self, ID, code: int = None) -> str:
        if ID is not None:
            _id: int = 0
            if isinstance (ID, str):
                _id = int (ID)
            if isinstance (ID, int):
                _id = ID
            dt  = datetime.now()
            if code is not None:
                id_str = "{0}_{1}_{2}".format(dt.strftime (self._id_fmt), _id, code)
                return id_str
            else:
                id_str = "{0}_{1}".format(dt.strftime (self._id_fmt), _id)
                return id_str

# =======================================================================================
# 
    def getSimulationRecords (self, count:int=20) -> dict:
        """
        Retrieve records for simulation of ipecs events.

        Parameters:
        @count: (int) number of records to return

        Returns:
        @records: (dict) dictionary of records
        """
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode

        records = {}
        try:
            if mongo_client is not None:
                if verbose_mode:
                    logger.debug (resources['db025'].format (count))
                db = mongo_client [str (config['db-name'])]
                col = config['collections']['ipecs-simulation']
                records = db[col].find ()
                logger.debug (resources['db026'].format (records.count()))
            return records, records.count()
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
# =======================================================================================
# Upload End of Day Statistics to Mongo DB
    def updateEODSummary (self, pay_load: dict) -> None:
        """
        Uploads end of day summary stats to the Mongo database.
        If the framework already exists, it will be updated.
        """
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode

        try:
            if mongo_client is not None and pay_load is not None:
                if verbose_mode:
                    logger.debug (resources['db024'].format ('End of Day summary'))
                db = mongo_client [str (config['db-name'])]
                col = config['collections']['eod-summary']
                db[col].insert_one (pay_load)
                logger.debug (resources['db023'].format ('End of Day summary'))
            return
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
# Upload Agent Login / Logout event to Mongo DB
    def logAgentEvent (self, pay_load: dict) -> None:
        """
        Uploads agent login event to the Mongo database.
        If the framework already exists, it will be updated.
        """
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode

        try:
            if mongo_client is not None and pay_load is not None:
                if verbose_mode:
                    logger.debug (resources['db024'].format ('Agent login/logout event'))
                db = mongo_client [str (config['db-name'])]
                col = config['collections']['agent-log']
                pay_load['_id'] = self._make_id (pay_load['stationID'])
                db[col].insert_one (pay_load)
                logger.debug (resources['db023'].format ('Agent login/logout event'))
            return
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
# Upload Agent summary stats after logout to Mongo DB
    def logAgentSummary (self, pay_load: dict):
        """
        Logs the agent summary to Mongo DB 
        """
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode

        try:
            if mongo_client is not None and pay_load is not None:
                if verbose_mode:
                    logger.debug (resources['db024'].format ('agent summary'))
                pay_load['_id'] = self._make_id (pay_load['sourceNumber'])
                db = mongo_client [str (config['db-name'])]
                col = config['collections']['agent-summary']
                db[col].insert_one (pay_load)
                logger.debug (resources['db023'].format ('agent summary'))
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
        finally:
            return
# Upload call summary / history to Mongo DB
    def logCallHistory (self, summary: dict):
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode

        try:
            if mongo_client is not None and summary is not None:
                if verbose_mode:
                    logger.debug (resources['db024'].format ('call history'))
                summary['_id'] = self._make_id (pay_load['stationID'])
                db = mongo_client [str (config['db-name'])]
                col = config['collections']['call-history']
                db[col].insert_one (summary)
                logger.debug (resources['db023'].format ('call history'))
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
# Upload an ipecs event to Mongo DB
    def logEvent (self, pay_load: dict, simulation: bool = False):
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode

        try:
            if mongo_client is not None and pay_load is not None:
                if verbose_mode:
                    logger.debug (resources['db024'].format ('iPECs event'))
                pay_load['_id'] = self._make_id (pay_load['sourceNumber'], int (pay_load['eventCode']))
                db = mongo_client [str (config['db-name'])]
                # Check if the event should be saved to the simulation collection or to normal event collection
                if simulation:
                    col = config['collections']['ipecs-simulation']
                else:    
                    col = config['collections']['ipecs-events']
                db[col].insert_one (pay_load)
                if verbose_mode:
                    logger.debug (resources['db023'].format ('iPECs event'))
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
        finally:
            return
# log a missed call to Mongo DB
    def logMissedCall (self, pay_load: dict):
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode

        try:
            if mongo_client is not None and pay_load is not None:
                if verbose_mode:
                    logger.debug (resources['db024'].format ('Missed call'))
                pay_load['_id'] = self._make_id (pay_load['sourceNumber'])
                db = mongo_client [str (config['db-name'])]
                col = config['collections']['missed_call']
                db[col].insert_one (pay_load)
                if verbose_mode:
                    logger.debug (resources['db023'].format ('Missed call'))
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
        finally:
            return
# log SMDR outbound call info
    def logSMDREvent (self, pay_load: dict):
        global mongo_client
        global resources
        global config
        global logger
        global verbose_mode

        try:
            if mongo_client is not None and pay_load is not None:
                if verbose_mode:
                    logger.debug (resources['db024'].format ('SMDR event'))
                upd = config['smdr-events']
                upd['_id'] = self._make_id (pay_load['sourceNumber'])
                upd['time'] = pay_load ['time']
                try:
                    upd['call-id'] = int (pay_load ['callRefID'])
                except:
                    upd['call-id'] = 0
                upd['source-type']          = pay_load['sourceType']
                upd['source-number']        = pay_load['sourceNumber']
                upd['destination-type']     = pay_load['destType']
                upd['destination-number']   = pay_load['destNumber']
                upd['talk-time']            = pay_load['data1']
                upd['outbound-number']      = pay_load['data2']
                db = mongo_client [str (config['db-name'])]
                col = config['collections']['smdr-events']
                db[col].insert_one (upd)
                logger.debug (resources['db023'].format ('SMDR event'))
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
        finally:
            return

    def copySimulationData (self):
        global mongo_client
        global resources
        global config
        global logger

        try:
            if mongo_client is not None:
                db = mongo_client [str (config['db-name'])]
                col = config['collections']['ipecs-simulation']
                dest = 'ipecs_simulation_1'
                #records = db[col].find ({"$or": [{"eventCode": 84}, {"eventCode": 11}, {"eventCode": 18}]})
                records = db[col].find ()
                for record in records:
                    try:
                        x = record['callRefID']
                        if x is not None:
                            pass
                    except:
                        record['callRefID'] = 'N/A'
                    db[dest].insert_one (record)
        except Exception as ex:
            logger.error (resources['err024'].format (self.__module__, ex))
        finally:
            return
            
    class iPECsMongoThread (threading.Thread):
        def __init__ (self, threadID: int, interval: int):
            global _isConnected
            global resources
            global config
            global mongo_client
            global logger

            threading.Thread.__init__(self)
            logger     = logging.getLogger (LOGGING_ID)
            self.threadID   = threadID
            self.name       = 'iPECsMongoThread'
            self.interval   = interval
            self.isKilled   = False

        def run (self):
            while True and not self.isKilled:
                try:
                    con_stat = mongo_client.admin.command ('ping')
                    if con_stat ['ok'] == 1.0:
                        logger.debug (resources['db017'].format (config['url'], config['port']))
                        _isConnected = True
                        time.sleep (self.interval)
                    else:
                        # There was an issue, log and continue
                        _isConnected = False
                        logger.warning (resources['db005']. format (config['url'], config['port']))
                        time.sleep (self.interval)
                        continue
                except Exception as ex:
                    raise (ex)

        def kill (self):
            self.isKilled = True

# Thread preparation classes
    class threadLogCallHistory (threading.Thread):
        def __init__ (self, pay_load: dict):
            super().__init__()
            self.pay_load = pay_load

        def run (self):
            ipecs_db_io.logCallHistory (self, pay_load=self.pay_load)
