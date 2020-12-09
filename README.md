# iPECs API Wrapper

The function of the iPECs API wrapper is to establish a connection to a iPECs server providing a REST API and to hide the complexities of the communication with said server.

## Copyright Notice
>**Copyright 2020 - Current by Peter Gossler. All Rights Reserved.**
>All information contained herein is, and remains the property of Peter Gossler and his suppliers, if any.  The intellectual and technical concepts contained herein are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean and Foreign Patents, patents in process, and are protected by trade secret or copyright law. Dissemination of this information or reproduction of this material is strictly forbidden unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

## Functional Overview
The **iPECs API Wrapper (Wrapper)** establishes communication with a server running the iPECs Contact Center Software and handles all requests as well as web socket communications with that server.

### Wrapper Framework
The Wrapper has been designed to run as *Middle Ware* on a server environment. Being designed in Python, it can run on any platform that supports Python Version 3.8>.
Since the Wrapper does not support any kind of direct user input, it has to be configured using [configuration information](#config) stored in permanent manner. At this point the implementation of configuration is through JSON files. At a later state the Wrapper might use a database such as Mongo to store the majority of the [configuration info](#config), but there still will be a dependancy on a small [configuration file](#config).

### Wrapper Launch Functionality
When first invoked by a control software the wrapper will go through its self-initialisation process. During this process it loads:
- the  [Configuration File](#config),
- the [Language Resource File](#resource),
- the [iPECS Commands Resources File](#ipecs),
- launches an [Event Logger](#logger),
- configures any URLs required,
- establishes communication with the specified iPECs host server via web socket,
- processes any events that are sent from the iPECs server,
- does some limited call center metrics capturing, and
- notifies the control software of any events through ***call backs***.

The Wrapper supports event logging into a log file which by default is located in ```/ipecs_api_install_dir/log/ipecsapi.log```

## Functions exposed by the iPECs API Wrapper
### ipecsAPI constructor
***wrapper = ipecsAPI (optional: f_name, optional: log_id)***
Function initialises the ipecsAPI class.

***Parameters***
f_name : the fully qualified path of the iPECsAPI configuration file, default is ```/ipecs_api_install_dir/res/ipecs.conf```
log_id : the name that will precede log entries in the log file and console log.

The function will raise an exception if anything goes wrong.

---

## Event Hooks
The wrapper notifies the parent software through event call back functions.
Generally, each of the call back functions can be configured by providing a function pointer the the appropriate add...Hook method as described below:  
assuming the object you created from the ipecsAPI class is wrapper, then adding an event hook would look like ```wrapper.addEventHook (function_pointer)```,  
where function pointer is a function you need to define in your code. This function will then be called (with a dictionary / json as a parameter) by the wrapper once an event of the desired type is received from the iPECs server. The following call back functions are available in version 0.5.0 of the iPECs API Wrapper:

### addEventHook (function ptr)
This is the main event hook, that will provide a summary view of the call status in the iPECs server.
```
addEventHook (my_call_back_handler)
```
Once the wrapper calls this call back function it provides a json object in the following format:
```
{
      "stations-connected":   0,
      "agents-logged-in":     0,
      "total-inbound-calls":  0,
      "total-answered-calls": 0,
      "total-abandoned-calls":0,
      "total-outbound-calls": 0,
      "total-logged-in-time": 0.0,
      "total-avail-time":     0.0,
      "total-unavail-time":   0.0,
      "total-idle-time":      0.0,
      "total-busy-time":      0.0,
      "total-hold-time":      0.0,
      "total-wrap-time":      0.0
}
```
### addNewCallHook (function ptr)
Will be called when a new call is received. Once called, the function returns a json object ```{"Total Calls": int}``` containing the total number of calls received up to that point.
```
addNewCallHook (my_call_back_handler)
```

### addCallDisconnectedHook (function ptr)
Will be called when a call is ended. Once called, the function returns a json object ```{"Active Calls": int}``` containing the total number of currently active calls.
```
addNewCallHook (my_call_back_handler)
```

### addCallAnsweredHook (function ptr)
Will be called when a call is answered by an agent. Once called, the function returns a json object ```{"Answered Calls": int}``` containing the total number of answered calls up to that point.
```
addCallAnsweredHook (my_call_back_handler)
```

### addCallWaitingHook (function ptr)
Will be called when a new call is placed in the queue (no agents available). Once called, the function returns a json object ```{"Calls In Queue": int}``` containing the total number of calls currently waiting in queue.
```
addCallWaitingHook (my_call_back_handler)
```

### addAgentLoggedInHook (function ptr)
Will be called when an agent logs into the ACD system. Once called, the function returns a json object ```{"Agents Logged In": int}``` containing the total number of agents currently logged into the system.
```
addAgentLoggedInHook (my_call_back_handler)
```

### addAgentLoggedOutHook (function ptr)
Will be called when an agent logs out of the ACD system. Once called, the function returns a json object ```{"Agents Logged In": int}``` containing the total number of agents currently logged into the system.
```
addAgentLoggedOutHook (my_call_back_handler)
```

### addStationConnectedHook (function ptr)
Will be called when someone logs into their hard-phone or soft-phone. Once called, the function returns a json object ```{"Stations connected": int}``` containing the total number of phones/stations currently logged into the system.
```
addStationConnectedHook (my_call_back_handler)
```

### addStationDisconnectedHook (function ptr)
Will be called when someone logs out their hard-phone or soft-phone. Once called, the function returns a json object ```{"Stations connected": int}``` containing the total number of phones/stations currently logged into the system.
```
addStationDisconnectedHook (my_call_back_handler)
```

### addStationBusyHook (function ptr)
Will be called when a station / phone becomes busy. Once called, the function returns a json object ```{"Busy Stations": int}``` containing the total number of answered calls up to that point.
```
addStationBusyHook (my_call_back_handler)
```
---

## Sample Parent Program (Python)
```python
from ipecsAPI import ipecsAPI

def main ():

    # define call back function for main event changes
    def onEvent (event_data: dict) -> None:
        print (event_data)
    # define call back function for when station logs in (call back will provide parameter {"Stations connected": list} - list of int with extension numbers)
    def onNewStationEvent (event_data: list) -> None:
        print (event_data)

    # Class wide variables
    ipecs: ipecsAPI

    # Get going....
    try:
        # Create ipecsAPI object
        ipecs = ipecsAPI ()
        # Add event handler hooks
        ipecs.addEventHook (onEvent)
        ipecs.addStationConnectedHook (onNewStationEvent)
        #
        # Add more event hooks  as you require
        #
        # Connect to the iPECs API server - login, create socket and keep listening
        ipecs.connectAPI ()

    except Exception as ex:
        print (ex)

if __name__ == '__main__':
    main()
```

## Dependencies

### Python Libraries/Modules

| Module/Library | Description | Installation |
| --- | ----------- | ----------- |
| **Python** | Version 3.8+ | ```https://www.python.org/downloads/```|
| **asyncio** | is a library to write concurrent code using the async/await syntax. | ```Part of Python``` |
| **base64** | provides functions for encoding binary data to printable ASCII characters and decoding such encodings back to binary data. It provides encoding and decoding functions for the encodings specified in RFC 3548, which defines the Base16, Base32, and Base64 algorithms, and for the de-facto standard Ascii85 and Base85 encodings.| ```Part of Python``` |
| **binascii** | the binascii module contains a number of methods to convert between binary and various ASCII-encoded binary representations. The binascii module contains low-level functions written in C for greater speed that are used by the higher-level modules. | ```Part of Python``` |
| **haslib** | implements a common interface to many different secure hash and message digest algorithms. Included are the FIPS secure hash algorithms SHA1, SHA224, SHA256, SHA384, and SHA512 (defined in FIPS 180-2) as well as RSA’s MD5 algorithm (defined in Internet RFC 1321. | ```Part of Python``` |
| **json** | A lightweight data interchange format inspired by JavaScript object literal syntax. | ```Part of Python``` |
| **logging** | This module defines functions and classes which implement a flexible event logging system for applications and libraries. | ```Part of Python``` |
| **os** | This module provides a portable way of using operating system dependent functionality. | ```Part of Python``` |
| **socket** | This module provides access to the BSD socket interface. It is available on all modern Unix systems, Windows, MacOS, and probably additional platforms. | ```Part of Python``` |
| **ssl** | This module provides access to Transport Layer Security (often known as “Secure Sockets Layer”) encryption and peer authentication facilities for network sockets, both client-side and server-side | ```Part of Python``` |
| **sys** | This module provides access to some variables used or maintained by the interpreter and to functions that interact strongly with the interpreter | ```Part of Python``` |
| **time** | This module provides various time-related functions | ```Part of Python``` |
| **Crypto** | PyCryptodome is a self-contained Python package of low-level cryptographic primitives. | ```1) sudo apt-get install build-essential python3-dev, 2) pip3  install pycryptodomex,  3) python3 -m Cryptodome.SelfTest``` |
| **pymongo** | The PyMongo distribution contains tools for interacting with MongoDB database from Python. | ```pip3 install pymongo``` |
| **requests** | The requests library is the de facto standard for making HTTP requests in Python | ```pip3 install requests``` |
| **urllib3** | urllib3 is a powerful, sanity-friendly HTTP client for Python. | ```pip3 install urllib3``` |
| **websockets** | is a library for building WebSocket servers and clients in Python with a focus on correctness and simplicity | ```pip3 install websockets``` |

### Other Dependencies
The iPECs API uses https and secure sockets. For the API Wrapper to function properly the system therefore needs to have the proper ssl certificates installed.
However, at this point SSL warnings are disabled in the code.
>TODO: add more detail about certificates - also see if at a later stage can develop an installation script that automatically install and configures the certificates.



## Still TODO
## Support Files
### <a name="conf">Configuration File</a>

### <a name="resource">Language Resource File</a>

### <a name="ipecs">iPECs Command File</a>

### <a name="logger">Event Log Function</a>

## TODO List
- [ ] add configuration file info
- [ ] add resource file info
- [ ] add command file info
- [ ] add event logger info
- [ ] add links to references within document
- [ ] add list of functions plus syntax
