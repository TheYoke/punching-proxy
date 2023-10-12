# Punching Proxy
Punching Proxy makes a host behind NAT as a proxy server using TCP hole Punching.  
it uses [rentry.co](https://rentry.co) as an intermediate server for initial IPs/ports exchange.

## How to use:
### Setup rentry.co url (only for first time)
- go to [rentry.co](https://rentry.co)
- insert something in the Text area
- insert and remember "custom edit code" and "custom url" at the buttom
- click "Go" (it will redirect to a new page)
- click "Edit"
- remove/empty anything inside the Text area
- enter your "custom edit code" in "Enter edit code"
- click "Save"

### Run proxy servers
- Clone this repo to the server and client
- Run `pip install -r requrements.txt` in the server and client
- run one of these commands first and then the other (recommend server.py first)
    - `python3 server.py rentry_id rentry_code [mitm_mode]` (for server)
    - `python3 client.py rentry_id rentry_code [proxy_port]` (for client)
- where `rentry_id` is "custom url" and `rentry_code` is "custom edit code" of [rentry.co](https://rentry.co)
- optional `mitm_mode` is currently support only for "regular" (HTTP proxy)
- optional `proxy_port` is local port to connect client
- after run `client.py`, it will print ip:port for the client side proxy