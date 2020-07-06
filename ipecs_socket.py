# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import asyncio
import websockets
from   websockets import WebSocketClientProtocol
import logging

class ipecs_web_socket:
    __log = logging.Logger
    __wssurl = ''
    __cnf = {}
    __res = {}

    def __init__ (self, logger, wss_url, config, resources):
        self.__log = logger
        self.__wssurl = wss_url
        self.__cnf = config
        self.__res = resources

    def __del__ (self):
        self.__log.info (self.__res['wss002'])
        del self.__wssurl
        del self.__res
        del self.__cnf
        del self.__log

    async def ipecs_handler (self, websocket : WebSocketClientProtocol) -> None:
        async for message in websocket:
            self.__log.info (self.__res['wss002'].format(message))
            
    async def consume (self) -> None:
        async with websockets.connect (self.__wssurl) as websocket:
            self.__log.info (self.__res['wss002'].format(self.__wssurl))
            await self.ipecs_handler (websocket)

