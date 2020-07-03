import requests
from requests.auth import HTTPBasicAuth
import logging
import os, ssl
import ipecsAPI

try:
    __log = logging.Logger
    # Create object from class so we get wrapper functions available
    api = ipecsAPI.ipecsAPI ()
    __log = api.getlogger ()
    url = api.getFullURI()

    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context

    command = 'login/'
    cmdurl = url+command

    headers = {
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36 Edg/83.0.478.45',
        'DNT': '1',
        'Content-type': 'application/json',
        'Accept': '*/*',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referrer': 'https://srsupply.fortiddns.com:8743/apidemo.html',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8'
        }
    response = requests.get(cmdurl, auth=HTTPBasicAuth('apiadmin', 'APIproject2020'), headers=headers, verify=False)
    json = response.json()
    __log.info (json)
except requests.exceptions.HTTPError:
    json = response.json()
    __log.error ("Error {json['error']}")
except requests.exceptions.SSLError as err:
    print (err)
except Exception as ex:
    __log.fatal (ex)