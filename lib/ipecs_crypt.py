# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import  os, logging, binascii, sys
import  base64, hashlib
from    Crypto.Cipher   import AES
from    Crypto          import Random

class ipecs_crypt:
    __config: dict
    __logger: logging.Logger

    def __init__ (self, keyFile: str, resources: dict, logger: logging.Logger):
        self._log = logger
        self._res = resources
        self._keyFile = keyFile
        self._log.info (self._res['enc010'])

    def _getKey (self):
        f_key = os.path.join (os.getcwd(), self._keyFile)
        self._log.debug (self._res['enc001'].format (f_key))
        if not os.path.exists(f_key):
            raise FileNotFoundError (f"The key file [{f_key}] does not exist!")
        else:
            f = open (f_key, 'rb')
            key = f.read ()
            f.close()
            self._log.debug (self._res['enc002'].format (f_key))
        return key

    def _pad (self, s):
        return s + (AES.block_size - len(s) % AES.block_size) * chr (AES.block_size - len(s) % AES.block_size)
    
    def _unpad (self, s):
        return s[:-ord(s[len(s) - 1:])]

    def encrypt(self, message, key_size=256):
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

    def decrypt(self, ciphertext):
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