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

from    pymongo     import cursor
from    pymongo     import MongoClient
from    pymongo     import errors as mdb_errors

_isConnected = False

class ipecs_db_io:
    def __init__ (self, resources:dict, config:dict, logger):
        """
        Initialises the ipecs_dbio class.
        
        Parameters
        ----------
        env: dictionary - contains the environment parameters
        cnf: dictionary - contains configuration parameters
        """
        try:
            self._log      = logger
            self._cnf      = config
            self._res      = resources
            self._client   = MongoClient()
            self._cnt_iv   = 0
            _isConnected   = False
            self.dbConnect ()
            self._log.debug (self._res['db020'].format(self.__class__))
        except Exception as e:
            raise Exception (e)

    def __del__ (self):
        if self._thread_mongo_status.isAlive():
            self._thread_mongo_status.kill()
            self._thread_mongo_status.join()
        self._client.close()
        del self._client
        del self._cnf
        del self._log
        del self._res

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
        con_stat = self._client.admin.command ('ping')
        if con_stat ['ok'] != 1.0:
            return 0
        else:
            return 1

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
        if url is None:
            url = self._cnf['url']
        if port is None:
            port = self._cnf['port']
        _current_attempt = current_retry
        try:
            self._log.info (str.format(self._res['db001'], url, port, self._cnf['connectTimeoutMS'], self._cnf['socketTimeoutMS']))
            self._client = MongoClient (url, port, connectTimeoutMS=self._cnf['connectTimeoutMS'], socketTimeoutMS=self._cnf['socketTimeoutMS'])
            try:
                # self._client.server_info ()
                self._thread_mongo_status = ipecs_db_io.iPECsMongoThread (threadID=100, 
                                            interval=self._cnf['connectionCheckTimeoutMS'], 
                                            client=self._client, 
                                            logger=self._log, 
                                            resources=self._res, 
                                            config=self._cnf)
                self._thread_mongo_status.daemon = True
                self._thread_mongo_status.start()
                self._isConnected = True
            # Mongo server is not responding
            except Exception:
                # check if the thread is alive and if yes, kill it
                if self._thread_mongo_status.is_alive():
                    self._thread_mongo_status.kill()
                    self._thread_mongo_status.join()
                self._log.warning (self._res['db019'].format(url), self._cnf['retry-rate'], _current_attempt + 1)
                if _current_attempt < self._cnf['retry-attempts']:
                    time.sleep (self._cnf['retry-rate'])
                    self.dbConnect (url=url, port=port, current_retry=_current_attempt + 1)
                else:
                    raise Exception (str.format (self._res['db003'], url, port))
        except Exception as ex:
            raise (ex)
        # We are connected
        self._log.info (str.format(self._res['db006'], url, port))

# ================== Upload Forecast Framework to MongoDB -- THREAD SAFE -- ==================
    def newCallEvent (self, event=None):
        """
        Uploads the forecast Framework defined in Excel or json file to the Mongo database.
        If the framework already exists, it will be updated.
        """
        try:
            self._log.info (str.format(self._res['db007'], self._cnf['db-name']))
            self.dbConnect (self._cnf['url'], self._cnf['port'])
            self._log.info (str.format(self._res['db002'], self._cnf['db-name']))

            if self._client is not None:
                db = self._client [str (self._cnf['db-name'])]
                #db.authenticate (self._cnf['user'], self._cnf['pw'])
                self._log.info (str.format(self._res['db002'], self._cnf['db-name']))

        except Exception as e:
            raise e
        
    def updateCallSummary (self, data: list):


    class iPECsMongoUpdateSummary (threading.Thread):
        def __init__ (self, threadID: int, client: MongoClient, logger: logging.Logger, resources: dict, config: dict, data: dict):
            threading.Thread.__init__(self)
            self.resources  = resources
            self.config     = config
            self.threadID   = threadID
            self.name       = 'mongoUpdateSummaryThread'
            self.client     = client
            self.data       = data
            self.logger     = logger
            self.isKilled   = False

        def run (self):
            try:
                if self._client is not None:
                    upd = self.config ['template-call-summary']
                    upd['TimeStamp']            = data[0]
                    upd['TotalCalls']           = data[1]
                    upd['AnsweredCalls']        = data[2]
                    upd['AbandonedCalls']       = data[3]
                    upd['TotalHandleTime']      = data[4]
                    if data [1] > 0:
                        upd['AverageHandleTime'] = round (number=(data[4] / data) [2], ndigits=3)
                    else:
                        upd['AverageHandleTime'] = 0.0

                    db = self.client [str (self.config['collections']['call-summary'])]
                    db.
                    #db.authenticate (self._cnf['user'], self._cnf['pw'])
                    self._log.info (str.format(self.resources['db002'], self.config['db-name']))

                # Log that update has been performed
                self.logger.info (self.resources['db021'])
            except Exception as ex:
                raise (ex)

    class iPECsMongoThread (threading.Thread):
        def __init__ (self, threadID: int, interval: int, client: MongoClient, logger: logging.Logger, resources: dict, config: dict):
            threading.Thread.__init__(self)
            self.resources  = resources
            self.config     = config
            self.threadID   = threadID
            self.name       = 'iPECsMongoThread'
            self.interval   = interval
            self.client     = client
            self.logger     = logger
            self.isKilled   = False

        def run (self):
            while True and not self.isKilled:
                try:
                    con_stat = self.client.admin.command ('ping')
                    if con_stat ['ok'] == 1.0:
                        self.logger.debug (self.resources['db017'].format (self.config['url'], self.config['port']))
                        _isConnected = True
                        time.sleep (self.interval)
                    else:
                        # There was an issue, log and continue
                        _isConnected = False
                        self.logger.warning (self.resources['db005']. format (self.config['url'], self.config['port']))
                        time.sleep (self.interval)
                        continue
                except Exception as ex:
                    raise (ex)

        def kill (self):
            self.isKilled = True
