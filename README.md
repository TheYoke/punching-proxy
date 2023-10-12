# Punching Proxy
Punching Proxy makes a host behind NAT as a proxy server by using TCP hole Punching.  
It uses [rentry.co](https://rentry.co) as an intermediate service for initial IPs/ports exchange.

## How to use
### Setup rentry.co url (only for first time)
- Go to [rentry.co](https://rentry.co)
- Insert something in the Text area
- Insert something and remember the "custom edit code" and the "custom url" at the bottom
- Click "Go" (it will redirect to a new page)
- Click "Edit"
- Remove/empty anything inside the Text area
- Enter your "custom edit code" in "Enter edit code"
- Click "Save"

### Run proxy servers
- Clone this repo to the server and client
- Run `pip install -r requrements.txt` in the server and client
- Run one of these commands first and then the other (recommend server.py first)
    - `python3 server.py rentry_id rentry_code [mitm_mode]` (for server)
    - `python3 client.py rentry_id rentry_code [proxy_port]` (for client)
- Where `rentry_id` is the "custom url" and `rentry_code` is the "custom edit code" of [rentry.co](https://rentry.co)
- Optional `mitm_mode` is currently support only for "regular" (HTTP proxy)
- Optional `proxy_port` is the local port to connect for client
- After run `client.py`, it will print ip:port for the client side proxy

## Use case example
Service like Google Colab can be use as a proxy server where you can change IP by delete runtime and reconnect to it.  
This is useful when a certain service limits number of access per IP (e.g. MEGA)
