# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import os, os.path, sys, stat
import asyncio, ssl, stat
import logging
import time
import websocket
import subprocess

STAT_0o775 = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH )


# -------------------------------------------------------------------------------------------------
#                   DEFINITION FOR CLASS IPECS_WEBSOCKET
# -------------------------------------------------------------------------------------------------
class ipecs_websocket:
    _uri: str
    _ip:  str
    _folder: str
    _port: int
    _cnf: dict
    _res: dict
    _event: dict
    _uid: str
    _ssl_context: ssl.SSLContext
    _log: logging.Logger
    _is_connected = False
    _has_error    = False

    def __init__ (self, logger, configuration, config, resources, port=None):
        self._ip = configuration.ipecs_ip
        self._port = configuration.ipecs_port
        self._uid = configuration.getUserID('ipecs')
        self._uri = self._cnf['socket-format'].format (
            self._ip, 
            self._port, 
            self._cnf['socket-folder'], 
            self._cnf['target'], 
            self._cnf['APIVersion'], 
            self._uid)
        del self._uid
        self._log.debug (resources['wss012'].format (self.__class__, self._port, self._uri))
        self._cnf = config
        self._folder = config['socket-folder']
        self._res = resources
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_OPTIONAL
        self._log.debug (self._res['http011'].format(self.__class__))
        #ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})

    def __del__ (self):
        self._log.info (self._res['wss002'].format(self._uri))
        try:
            if isInstance (self._uri, str):
                del self._uri
        except:
            pass
        try:
            if isInstance (self._ip, str):
                del self._ip
        except:
            pass
        try:
            if isInstance (self._folder, str):
                del self._folder
        except:
            pass
        try:
            if isInstance (self._res, dict):
                del self._res
        except:
            pass
        try:
            if isInstance (self._cnf, dict):
                del self._cnf
        except:
            pass
        try:
            if isInstance (self._log, logging.Logger):
                del self._log
        except:
            pass

    def startSocketListener (self):
        self._log.debug (self._res['wss011'])
        try:
            asyncio.get_event_loop().run_until_complete(asyncio.wait([self.alive(), self.async_processing()]))
        except:
            self._has_error = True
        if self._has_error and not self._is_connected: 
            raise websockets.exceptions.ConnectionClosedError
        self._is_connected = True
        self._log.info (self._res['wss008'].format(self._ip))

    async def alive(self):
        while self._is_connected:
            self._log.debug (self._res['wss015'])
            await asyncio.sleep(self._cnf['socket-timeout'])

    async def async_processing(self):
        try:
            #async with websockets.connect(self._uri, ssl=self._ssl_context, ping_interval=self._cnf['socket-timeout'] * 0.95, ping_timeout=self._cnf['ping-timeout']) as websocket:
            
            async with websockets.connect(self._uri, ssl=self._ssl_context) as websocket:
                while True:
                    try:
                        message = await websocket.recv()
                        self._event = message
                        self._log.info (message)

                    except websockets.exceptions.ConnectionClosed:
                        self._log.warning (self._res['wss014'].format (self._ip))
                        self._is_connected = False
                        break
        except Exception as ex:
            self._has_error = True
            self._log.error (self._res['wss013'].format (ex, self._ip))
            raise Exception (ex)
    
    def onMessage (self):

