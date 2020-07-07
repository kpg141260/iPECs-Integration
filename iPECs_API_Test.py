# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import requests
from   requests.auth import HTTPBasicAuth
import json
import logging
import os
import ipecsAPI
import ipecs_socket

try:
    ipecs = ipecsAPI.ipecsAPI ()
    opcodes = ipecs.getOpCodes ()
    config  = ipecs.getConfiguration (section='URI')
    uid = 'apiadmin'
    pwd = 'APIproject2020'

    # Log into the iPECs API
    ipecs.sendCommand ('login', user=uid, pw=pwd)

    # Initiate Secure WEB Socket
    wss = ipecs_socket.ipecs_web_socket (ipecs.getlogger(), ipecs.getbaseWSS(), ipecs.getConfiguration(section='URI'), ipecs.getResources(section='wss'))

    # Return the total number of records in the iPECs database
    json = ipecs.sendCommand ('smdr', user=uid, arg1=opcodes['smdr-get-record-count'])
    print ("Total records in iPECs database: " + str (json['count']))
    # Return the first 50 records from the iPECs database (each query is limited to 50 records)
    req = opcodes['smdr-get-record-all']
    req['maxCount'] = 240
    json = ipecs.sendCommand ('smdr', user=uid, arg1=req)
    for key, value in json.items():
        if key == 'count':
            print (key, value)
        if key == 'items':
            tmp = value
    for i in range (0, len(tmp), 1):
        print (tmp[i]['Index'], tmp[i]['StationNumber'],tmp[i]['Duration'])
    print ("Records retrieved from iPECs database: " + str (json['count']))
    ipecs.sendCommand ('logout', user='apiadmin')

# ================== Error Handling and Exit ===================================
except Exception as ex:
    logging.critical ("[iPECs_API_Test.py ->> Abnormal program termination! --> [{0}]".format(ex))
finally:
    logging.shutdown()