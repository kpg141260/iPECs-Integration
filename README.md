# iPECs API Wrapper

The function of the iPECs API wrapper is to establish a connection to a iPECs server providing a REST API and to hide the complexities of the communication with said server.

## Copyright Notice
>**Copyright 2020 - Current by Peter Gossler. All Rights Reserved.**
>All information contained herein is, and remains the property of Peter Gossler and his suppliers, if any.  The intellectual and technical concepts contained herein are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean and Foreign Patents, patents in process, and are protected by trade secret or copyright law. Dissemination of this information or reproduction of this material is strictly forbidden unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

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
| **Autobahn** | is part of the Autobahn project and provides open-source implementations of the WebSocket Protocol and he Web Application Messaging Protocol (WAMP) for Python 3.5+ running on Twisted or asyncio. Autobahn runs on top of Twisted and asyncio Python frameworks| ```pip3 install autobahn``` |
| **requests** | The requests library is the de facto standard for making HTTP requests in Python | ```pip3 install requests``` |
| **Crypto** | PyCryptodome is a self-contained Python package of low-level cryptographic primitives. | ```1) sudo apt-get install build-essential python3-dev, 2) pip3  install pycryptodomex, 3) python3 -m Cryptodome.SelfTest``` |
| **Twisted** | is an event-driven networking engine written in Python. It supports CPython 2.7, CPython 3.5+, PyPy2, and PyPy3. | ```pip3 install twisted[tls]``` |
| **urllib3** | urllib3 is a powerful, sanity-friendly HTTP client for Python. | ```pip3 install urllib3``` |
| **websockets** | is a library for building WebSocket servers and clients in Python with a focus on correctness and simplicity | ```pip3 install websockets``` |

### Other Dependencies
The iPECs API uses https and secure sockets. For the API Wrapper to function properly the system therefore needs to have the proper ssl certificates installed.
>TODO: add more detail about certificates - also see if at a later stage can develop an installation script that automatically install and configures the certificates.

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
