So far what I have figured out is the communication to the SMDR portion of the system.
So, here is what goes on:
## Login Request:

```json
  GET https://srsupply.fortiddns.com:8743/ipxapi/server/v1/users/SMDR2api/login HTTP/1.1
  Host: srsupply.fortiddns.com:8743
  Connection: keep-alive
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36 Edg/83.0.478.37
  DNT: 1
  Authorization: Basic U01EUjJhcGk6c21kcjJhcGlwcm9qZWN0
  Content-type: application/json
  Accept: */*
  Sec-Fetch-Site: same-origin
  Sec-Fetch-Mode: cors
  Sec-Fetch-Dest: empty
  Referer: https://srsupply.fortiddns.com:8743/apidemo.html
  Accept-Encoding: gzip, deflate, br
  Accept-Language: en-GB,en;q=0.9,en-US;q=0.8
```

### Login Reply:

```json
HTTP/1.1 200 OK
Cache-control: no-cache
Content-Length: 220
Content-Type: application/json
Connection: Keep-Alive
Keep-Alive: timeout=5, max=100
{
	"token": "-bOy2A-jvRR1yxU-wbq1wxeItfSlCvHafBsouYTYvRU",
	"checkConnectionTimer": 120,
	"systemType": "iPECS UCP600",
	"systemVersion": "S-UCP-Tmp2004-4.0.18-App",
	"apiVersion": "1.0.0",
  "terminalCount": 2400
}
```
```json
GET https://srsupply.fortiddns.com:8743/ipxapi/server/v1/users/SMDR2api/login?token=-bOy2A-jvRR1yxU-wbq1wxeItfSlCvHafBsouYTYvRU HTTP/1.1
Host: srsupply.fortiddns.com:8743
Connection: Upgrade
Pragma: no-cache
Cache-Control: no-cache
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36 Edg/83.0.478.37
Upgrade: websocket
Origin: https://srsupply.fortiddns.com:8743
Sec-WebSocket-Version: 13
Accept-Encoding: gzip, deflate, br
Accept-Language: en-GB,en;q=0.9,en-US;q=0.8
Sec-WebSocket-Key: HkYhzOiN8wgypDVb48TUJg==
Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits
```
```json
HTTP/1.1 101 Switching Protocols
Upgrade: WebSocket
Connection: Upgrade
Sec-WebSocket-Accept: fmB2vWuC47UBo4MqBicFoYsIX8s=
```

## Get ACD Agent LogOn:

```json
POST https://srsupply.fortiddns.com:8743/ipxapi/server/v1/users/SMDR2api/call/agent_logon HTTP/1.1
Host: srsupply.fortiddns.com:8743
Connection: keep-alive
Content-Length: 183
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36 Edg/83.0.478.37
DNT: 1
Authorization: Bearer -bOy2A-jvRR1yxU-wbq1wxeItfSlCvHafBsouYTYvRU
Content-type: application/json
Accept: */*
Origin: https://srsupply.fortiddns.com:8743
Sec-Fetch-Site: same-origin
Sec-Fetch-Mode: cors
Sec-Fetch-Dest: empty
Referer: https://srsupply.fortiddns.com:8743/apidemo.html
Accept-Encoding: gzip, deflate, br
Accept-Language: en-GB,en;q=0.9,en-US;q=0.8

{
  "transactionID":1590650015556,
  "data":{
    "deviceNumber":"PHONEDIGIT_STRING",
    "agentId":"4_DIGITS",
    "groupNumber":"PHONEDIGIT_STRING",
    "loginPrimary":"primary|secondary",
    "loginPriority":9
    }
  }
```

### Reply <- looks there is a authorisation problem still

```json
HTTP/1.1 400 Bad Request
Content-length: 89

{
	"error": {
		"code": 2,
		"message": "Resource is not allowed for this user"
	}
}
```

## What is my setup for testing?

I am using a Windows 10 Pro Workstation with Edge and [Fiddler 4](https://www.telerik.com/download/fiddler) installed on the same machine. Fiddler is acting as a man in the middle proxy, so you need to configure your web browser settings to point to the local IP with the port you define during install. Once this stuff works, Fiddler will decrypt the traffic that comes back from the web site you are monitoring, in this case [iPecs API demo](https://srsupply.fortiddns.com:8743/apidemo.html).
I attached a complete session log from login, send two commands to logout.
