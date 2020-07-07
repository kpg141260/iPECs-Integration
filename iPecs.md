# iPECs API Wrapper

The function of the iPECs API wrapper is to establish a connection to a iPECs server providing a REST API and to hide the complexities of the communication with said server.

## Copyright Notice
>**Copyright 2020 - Current by Peter Gossler. All Rights Reserved.**
>All information contained herein is, and remains the property of Peter Gossler and his suppliers, if any.  The intellectual and technical concepts contained herein are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean and Foreign Patents, patents in process, and are protected by trade secret or copyright law. Dissemination of this information or reproduction of this material is strictly forbidden unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

## Dependencies

| Module | Description | Installation |
| ----------- | ----------- | ----------- |
| Python | Version 3.8> | ```https://www.python.org/downloads/```|
| websockets | is a library for building WebSocket servers and clients in Python with a focus on correctness and simplicity | ```pip3 install websockets``` |
| requests | The requests library is the de facto standard for making HTTP requests in Python | ```pip3 install requests``` |
| urllib3 | urllib3 is a powerful, sanity-friendly HTTP client for Python. | ```pip3 install urllib3``` |
| json | A lightweight data interchange format inspired by JavaScript object literal syntax | ```Part of Python``` |
| os | This module provides a portable way of using operating system dependent functionality | ```Part of Python``` |
| ssl | This module provides access to Transport Layer Security (often known as “Secure Sockets Layer”) encryption and peer authentication facilities for network sockets, both client-side and server-side | ```Part of Python``` |
| sys | This module provides access to some variables used or maintained by the interpreter and to functions that interact strongly with the interpreter | ```Part of Python``` |
| time | This module provides various time-related functions | ```Part of Python``` |
| socket | This module provides access to the BSD socket interface. It is available on all modern Unix systems, Windows, MacOS, and probably additional platforms | ```Part of Python``` |
| logging | This module defines functions and classes which implement a flexible event logging system for applications and libraries | ```Part of Python``` |

## Functional Overview
The **iPECs API Wrapper (Wrapper)** establishes communication with a server running the iPECs Contact Center Software and handles all requests as well as web socket communications with that server.

### Wrapper Framework
The Wrapper has been designed to run as *Middle Ware* on a server environment. Being designed in Python, it can run on any platform that supports Python Version 3.8 or later.
Since the Wrapper does not support any kind of direct user input, it has to be configured using [configuration information](#config) stored in permanent manner. At this point the implementation of configuration is through JSON files. At a later state the Wrapper might use a database such as Mongo to store the majority of the [configuration info](#config), but there still will be a dependance on a small [configuration file](#config).

### Wrapper Launch Functionality
When first invoked by a control software the wrapper will go through its self-initialisation process. During this process it loads:
- the  [Configuration File](#config),
- the [Language Resource File](#resource),
- the [iPECS Commands Resources File](#ipecs),
- launches an [Event Logger](#logger),
- configures any URLs required, handles
- tries to establish communication with the specified iPECs host server.

The Wrapper supports event logging into a log file.

## Support Files
### <a name="conf">Configuration File</a>

### <a name="resource">Language Resource File</a>

### <a name="ipecs">iPECs Command File</a>

### <a name="logger">Event Log Function</a>

## Function Overview

## TODO List
- [ ] add configuration file info
- [ ] add resource file info
- [ ] add command file info
- [ ] add event logger info
- [ ] add links to references within document
- [ ] add list of functions plus syntax
