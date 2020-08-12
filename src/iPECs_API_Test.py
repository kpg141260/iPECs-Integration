# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import os, sys

def main ():
    tmp = os.path.join(os.getcwd(), 'lib')
    paths = sys.path
    try:
        paths.index (tmp)
    except ValueError as ex:
        sys.path.append(tmp)
    import  json
    import  logging
    import  asyncio
    from    ipecsAPI        import ipecsAPI
    from    ipecs_crypt     import ipecs_crypt
    #from    ipecs_socket    import ipecs_websocket

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ipecs: ipecsAPI
    local_logger: logging.Logger
    try:
        ipecs           = ipecsAPI (f_name=os.path.join(os.getcwd(), 'res', 'ipecs.conf'), log_id='iPECsAPI')
        local_logger    = ipecs.Logger
        opcodes         = ipecs.op_codes
        config_ipecs    = ipecs.getConfiguration (section='ipecs')
        config_mongo    = ipecs.getConfiguration (section='mongo')
        resource_http   = ipecs.getResources (section='http')
        local_logger.debug (ipecs.getResourceString('msg', 'msg003').format(__name__))

        # Log into the iPECs API - user info is derived from configuration file
        ipecs.sendCommand ('login')
        if not ipecs.UserLoggedIn:
            raise ipecs.LoginRetryAttemptsExceeded ()
        # Initiate Secure WEB Socket - this part can only run after successfull login
        wss_main = ipecs.startSocketListener ()
        # Update certifcate file bundle
        #wss_main.updateCertifiBundle ()
        #wss_main.startSocketListener ()

        # Return the total number of records in the iPECs database
        json = ipecs.sendCommand ('smdr', arg1=opcodes['smdr-get-record-count'])
        print ("Total records in iPECs database: " + str (json['count']))
        # Return the first 50 records from the iPECs database (each query is limited to 50 records)
        req = opcodes['smdr-get-record-all']
        req['maxCount'] = 240
        json = ipecs.sendCommand ('smdr', arg1=req)
        for key, value in json.items():
            if key == 'count':
                print (key, value)
            if key == 'items':
                tmp = value
        for i in range (0, len(tmp), 1):
            print (tmp[i]['Index'], tmp[i]['StationNumber'],tmp[i]['Duration'])
        local_logger.info ("Records retrieved from iPECs database: " + str (json['count']))
        ipecs.sendCommand ('logout')

    # ================== Error Handling and Exit ===================================
    except json.JSONDecodeError as ex:
        msg = "[iPECs_API_Test.py --> Error decoding json file! --> [{0}]".format(ex)
        logging.error (msg=msg, exc_info=False)
    except KeyError as ex:
        msg = "[iPECs_API_Test.py --> Dictionary key not found! --> [{0}]".format(ex)
        if logging.getLevelName == logging.DEBUG:
            logging.error (msg=msg, exc_info=True)
        else:
            logging.error (msg=msg, exc_info=False)
    except ipecs.ConnectionRefused as ex:
        msg = "[iPECs_API_Test.py --> Abnormal program termination! --> [{0}], HTTP error [{1}] - module cannot continue!".format(ex.args[0], ex.status_code)
        if logging.getLevelName == logging.DEBUG:
            logging.fatal (msg=msg, exc_info=True)
        else:
            logging.fatal (msg=msg, exc_info=False)
    except Exception as ex:
        msg = "[iPECs_API_Test.py --> Abnormal program termination! --> [{0}]".format(ex)
        if logging.getLevelName == logging.DEBUG:
            logging.error (msg=msg, exc_info=True)
        else:
            logging.error (msg=msg, exc_info=False)
    finally:
        try:
            if isinstance (ipecs, ipecsAPI):
                ipecs.shutdown()
                del ipecs
        except:
            pass
        try:
            if isinstance (opcodes, dict):
                del opcodes
        except:
            pass
        try:
            if isinstance (config_ipecs, dict):
                del config_ipecs
        except:
            pass
        try:
            if isinstance (config_mongo, dict):
                del config_mongo
        except:
            pass
        try:
            if isinstance (local_logger, logging.Logger):
                del local_logger
        except:
            pass
        logging.info ('iPECs_API_Test shutdown complete.')
        sys.exit()

if __name__ == '__main__':
    main()
