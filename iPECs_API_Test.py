import requests
from requests.auth import HTTPBasicAuth
import logging
import os
import ipecsAPI

__log   = logging.Logger
__res   = {}
# Create object from class so we get wrapper functions available
api     = ipecsAPI.ipecsAPI ()
__log   = api.getlogger ()
__res   = api.getResources ()
url     = api.getFullURI()
ip      = api.getiPECsServerIP ()  

__log.debug ("Attemting login to iPECs API...")
api.ipecsLogin ()
