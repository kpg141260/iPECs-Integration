import requests
from requests.auth import HTTPBasicAuth
import json
import logging
import os
import ipecsAPI

try:
    ipecs = ipecsAPI.ipecsAPI ()
    opcodes = ipecs.getOpCodes ()
    uid = 'apiadmin'
    pwd = 'APIproject2020'

    # Log into the iPECs API
    ipecs.sendCommand ('login', user=uid, pw=pwd)
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