        async def ipecs_handler (self, websocket : WebSocketClientProtocol, logger) -> None:
            async for message in websocket:
                logger.info (message)

        async def wss_listener (self, logger, ssl_context, uri, host_port, resource) -> None:
            logger.info (resource['wss008'].format(uri))
            try:
                async with websockets.connect (uri=uri, port=host_port, ssl=ssl_context) as websocket:
                    await self.ipecs_handler (websocket, logger)
                logger.info (resource['wss001'].format(uri))
            except ssl.SSLError as ex:
                logger.info (resource['wss009'].format(uri))
                raise (ex)
            except TypeError as ex:
                logger.info (resource['wss009'].format(uri))
                raise (ex)
            except Exception as ex:
                raise (ex)

# -------------------------------------------------------------------------------------------------
#    CREATE SOCKET CONSUMER
# -------------------------------------------------------------------------------------------------
    def createWSSconsumer (self, ip, port, logger) -> None:
        try:
            connection_str = "{}{}:{}/ipxapi".format("wss://", ip, str (port))
            factory = WebSocketClientFactory(connection_str)
            factory.protocol = iPECsClientProtocol ()

            self.__loop = asyncio.get_event_loop()
            coro = self.__loop.create_connection (factory, ip, port)
            self.__loop.run_until_complete(coro)

            try:
                self.__loop.run_forever()
            except KeyboardInterrupt:
                pass
            finally:
                coro.close()
                self.__loop.close()

        except Exception as ex:
            logger.error (ex)

    def onConnectEvent (self, response):
        __log.info (self.__res['wss004'].format(response))

    def onConnectingEvent(self, transport_details):
        __log.info(self.__res['wss010'].format(transport_details))

    def onMessageEvent(self, payload, isBinary):
        if isBinary:
            __log.info("Binary message received: {0} bytes".format(len(payload)))
        else:
            __log.info("Text message received: {0}".format(payload.decode('utf8')))
        
    def onCloseEvent (self, reason):
        __log.info (self.__res['wss002'].format(reason))        

        #self.get_certificate (host=self.__ip, port=self.__cnf['Port'], timeout=self.__cnf['timeout'], 
        #                      retry_attempts=self.__cnf['retry-attempts'], retry_rate=self.__cnf['retry-rate'], current_attempt=0)
        #self.createWSSconsumer ()
        #self.wss_producer = self.wss_producer (logger, uri, config, resources)

import subprocess, socket
from cryptography                   import x509
from cryptography.hazmat.backends   import default_backend
STAT_0o775 = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH )

# -------------------------------------------------------------------------------------------------
#    FORCE AN UPDATE OF THE CERTIFI CERTIFICATE BUNDLE
# -------------------------------------------------------------------------------------------------
    def updateCertifiBundle (self) -> None:
        openssl_dir, openssl_cafile = os.path.split(ssl.get_default_verify_paths().openssl_cafile)

        # Make sure that certifi library is installed
        self._log.info (self._res['ssl001'])
        try:
            subprocess.check_call([sys.executable, "-E", "-s", "-m", "pip", "install", "--upgrade", "certifi"])
        except subprocess.CalledProcessError as e:
            self._log.error (self._res['ssl002'].format (e.returncode))
            raise RuntimeError (e)

        self._log.info (self._res['ssl003'])

        import certifi

        path = os.getcwd()
        try:
            # Change working directory to the default SSL directory
            os.chdir(openssl_dir)
            relpath_to_certifi_cafile = os.path.relpath(certifi.where())
            self._log.info (self._res['ssl004'])
            try:
                os.remove(openssl_cafile)
            except FileNotFoundError:
                pass
            self._log.info (self._res['ssl005'])
            os.symlink(relpath_to_certifi_cafile, openssl_cafile)
            self._log.info (self._res['ssl006'])
            os.chmod(openssl_cafile, STAT_0o775)
            self._log.info (self._res['ssl007'])
        except Exception as ex:
            self._log(ex)
        finally:
            os.chdir (path)
        
        cert = self.get_certificate ()

        print('SSL Error. Adding custom certs to Certifi store...')
        cafile = certifi.where()
#        with open('certicate.pem', 'rb') as infile:
#            customca = infile.read()
        with open(cafile, 'ab') as outfile:
            outfile.write(cert)
        print('That might have worked.')



# -------------------------------------------------------------------------------------------------
#    RETRIEVE A CERTIFICATE FROM A SPECIFIED SERVER AND STORE IT IN OPENSSL CERTIFICATE BUNDLE
# -------------------------------------------------------------------------------------------------
    def get_certificate(self, host, port, timeout=3, retry_attempts: int = 3, 
                        retry_rate: int = 2, current_attempt: int = 0):

            socket.setdefaulttimeout(timeout)  # Set Socket Timeout

            try:
                # Signal intention to connect to host and fetch certificate
                __log.info(self.__res['wss005'].format(host, port))
                cert = ssl.get_server_certificate(addr=(host, port))

            except socket.timeout:
                # Out of attempts - raise an error
                if current_attempt == retry_attempts:
                    raise RuntimeError(self.__res['wss006'].format (host, port, retry_attempts))
                # Signal that we are going to retry the connection after a timeout
                __log.warning(self.__res['wss007'].format(host, retry_rate))
                # go to sleep for a while
                time.sleep(retry_rate)
                return self.get_certificate(host, port, timeout, retry_attempts, retry_rate, current_attempt + 1)
            else:
                certificate = x509.load_pem_x509_certificate(cert.encode(), backend=default_backend())
                return certificate 

# -------------------------------------------------------------------------------------------------
#                   DEFINITION FOR CLASS IPECS_WEBSOCKET.WSS_CONSUMER
# -------------------------------------------------------------------------------------------------
class iPECsClientProtocol (WebSocketClientProtocol):
    _log: logging.Logger

    def onConnect(self, response):
        self._log = logging.getLogger ('iPECsAPI')
        self._log.info (response=response.peer)

    def onConnecting(self, transport_details):
        print (transport_details)
        return None  # ask for defaults

    def onOpen (self):
        def hello():
            self.sendMessage("Hello, world!".encode('utf8'))
            self.sendMessage(b"\x00\x01\x03\x04", isBinary=True)
            __factory.loop.call_later(120, hello)
        # start sending messages every 120 seconds ..
        hello()

    def onMessage(self, payload, isBinary):
        print (payload, isBinary)
    
    def onClose (self, wasClean, code, reason):
       self._log.info (reason)        

# -------------------------------------------------------------------------------------------------
#
#                   DEFINITION FOR CLASS IPECS_WEBSOCKET.WSS_PRODUCER
#
# -------------------------------------------------------------------------------------------------
class wss_producer:
    __log = logging.Logger
    __uri = ''
    __cnf = {}
    __res = {}

    def __init__ (self, logger, uri, config, resources):
        __log = logger
        self.__uri = uri
        self.__cnf = config
        self.__res = resources

# getConfiguration - Provide pointer to configuration file
    """
    Function getConfiguration() -> dictionary.
    
    Parameters
    ----------
    section :   <str> specifies the sub-section of the dictionary to return.
                default is to return all sections.

    The function returns an object of type {dict} containing the configuration settings.
    """
    def getConfiguration (self, section=None) -> dict:
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        try:
            return self._config.getSection (section)
        except KeyError as ex:
            raise KeyError (ex)

# getHeaders - Provide pointer to ipecs headers
    """
    Function getHeaders.
    
    Parameters
    ----------
    none : nil.

    The function returns an object of type {json} containing the iPECs http header strings needed for command execution.
    """
    def getHeaders (self) -> dict:
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        try:
            return self._config.getiPECsCommands (section='headers')
        except KeyError as ex:
            raise KeyError (ex)

# getResponses - Provide pointer to ipecs responses
    """
    Function getResponses.
    
    Parameters
    ----------
    none : nil.

    The function returns an object of type {json} containing the iPECs http response types generated by command execution.
    """
    def getResponses (self) -> dict:
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        try:
            return self._config.getiPECsCommands (section='responses')
        except KeyError as ex:
            raise KeyError (ex)

# getOpCodes - Provide pointer to ipecs op-codes
    """
    Function getOpCodes.
    
    Parameters
    ----------
    none : nil.

    The function returns an object of type {json} containing the iPECs command operation codes.
    """
    def getOpCodes (self) -> dict:
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        try:
            return self._config.getiPECsCommands (section='op-codes')
        except KeyError as ex:
            raise KeyError (ex)

# getiPECsCommands - Provide pointer to iPECs command related info
    """
    Function getiPECsCommands() -> dictionary.
    
    Parameters
    ----------
    section :   <str> specifies the sub-section of the dictionary to return.
                default is to return all sections.

    The function returns an object of type {dict} containing the language strings.
    """
    def getiPECsCommands (self, section=None) -> dict:
        if not self._isInitialised:
            raise RuntimeError (self._notInitErr)
        try:
            return self._config.getiPECsCommands (section)
        except KeyError as ex:
            raise KeyError (ex)

    def _pad (self, s):
        return s + (AES.block_size - len(s) % AES.block_size) * chr (AES.block_size - len(s) % AES.block_size)

    def _unpad (self, s):
        return s[:-ord(s[len(s) - 1:])]

    def _encrypt(self, message, key_size=256):
        try:
            self._log.debug (self._res['enc006'])
            key = self._getKey ()
            msg = self._pad(message)
            txt = bytes (msg, 'utf-8')
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            enc = iv + cipher.encrypt(txt)
            self._log.debug (self._res['enc008'])
            return base64.b64encode(enc)
        except Exception as ex:
            raise (ex)

    def _decrypt(self, ciphertext):
        try:
            self._log.debug (self._res['enc007'])
            key = self._getKey ()
            ciphertext = base64.b64decode (ciphertext)
            iv = ciphertext[:AES.block_size]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            text_bytes = self._unpad (cipher.decrypt(ciphertext[AES.block_size:]))
            plaintext = str (text_bytes, 'utf-8')
            self._log.debug (self._res['enc009'])
            return plaintext
        except Exception as ex:
            raise (ex)


# -------------------------------------------------------------------------------------------------
#    RETRIEVE A CERTIFICATE FROM A SPECIFIED SERVER AND STORE IT IN OPENSSL CERTIFICATE BUNDLE
# -------------------------------------------------------------------------------------------------
def get_certificate(host='srsupply.fortiddns.com', port=8743, timeout=3, retry_attempts: int = 3, retry_rate: int = 2, current_attempt: int = 0):

        socket.setdefaulttimeout(timeout)  # Set Socket Timeout

        try:
            # Signal intention to connect to host and fetch certificate
            print ("Trying to fetch host's [{0}] TLS certificate...".format(host))
            cert = ssl.get_server_certificate(addr=(host, port))

        except socket.timeout:
            # Out of attempts - raise an error
            if current_attempt == retry_attempts:
                raise RuntimeError("No Response from host [{0}:{1}] after {2} attempts, aborting connection attempt.".format (host, port, retry_attempts))
            # Signal that we are going to retry the connection after a timeout
            print ("No response from host [{0}]. Retrying in {1} seconds...".format(host, retry_rate))
            # go to sleep for a while
            time.sleep(retry_rate)
            return get_certificate(timeout, retry_attempts, retry_rate, current_attempt + 1)
        else:
            certificate = x509.load_pem_x509_certificate(cert.encode(), backend=default_backend())
            print (certificate)
            return certificate 

    def startSocketListener ():
        websocket.enableTrace(True)
        protocol_str = self._config.getiPECsHeader (section=hdr_wss)
        protocol_str = protocol_str.format (self._sessiontoken)
        ws = websocket.WebSocketApp(self._fullWSS,
                            on_open = on_open,
                            on_message = on_message,
                            on_error = on_error,
                            on_close = on_close, 
                            header = [protocol_str]
                            )
        ws.run_forever()

    def on_message(ws, message):
        print ('message received ..')
        print (message)


    def on_error(ws, error):
        print ('error happened .. ')
        print (error)


    def on_close(ws):
        print ("### closed ###")

    def on_open(ws):
        print ('Opening Websocket connection to the server ... ')

