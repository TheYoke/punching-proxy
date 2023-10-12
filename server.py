#!/usr/bin/python3

from helpers import PortExchangeHelper, get_avail_port

from threading import Thread, Lock
import socket
import select
import subprocess
import shlex
import sys


def start_mitmdump(mode='regular'):
    ''' mode is one of "regular" (HTTP), "transparent", "socks5" '''

    # check for mitmdump existance
    subprocess.call(['mitmdump', '--version'], stdout=subprocess.DEVNULL)

    port = get_avail_port()
    args = shlex.split('mitmdump --listen-port %s --mode %s --ignore-host ".*" --set stream_large_bodies=1' % (port, mode))
    mitm = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return mitm, port


def estb_px(rentry_id, rentry_code):
    px = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        px.bind(('', 0))
        with PortExchangeHelper(rentry_id, rentry_code) as helper:
            pub_addr = (helper.get_public_ipv4(), px.getsockname()[1])

            addrs = helper.get()
            if len(addrs) == 0:
                dst_addr = helper.put_one_wait_two(pub_addr)
                helper.put([])
            elif len(addrs) == 1:
                dst_addr = addrs[0]
                helper.put(addrs + [pub_addr])
                helper.wait_empty()
            else:
                assert 0, f'unexcepted addrs length, {addrs}'
            
        px.connect(dst_addr)
    except:
        px.close()
        raise
    return px, dst_addr


def main():
    if len(sys.argv) in [3, 4]:
        rentry_id = sys.argv[1]
        rentry_code = sys.argv[2]
        mitm_mode = sys.argv[3] if len(sys.argv) == 4 else 'regular'
    else:
        print('Usage:', sys.argv[0], 'rentry_id rentry_code [mitm_mode]')
        return 1
    
    mitm, mitm_port = start_mitmdump(mitm_mode)
    px, px_dst_addr = estb_px(rentry_id, rentry_code)

    rlist = []
    proxy_conns = {}
    remote_conns = {}
    px_lock = Lock()


    def px_thread():
        while True:
            signal = px.recv(2)
            if signal == b'\x00\x00':
                # client keeps connection alive
                continue

            remote_dst_addr = px_dst_addr[0], int.from_bytes(signal, 'big')
            proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy.connect(('127.0.0.1', mitm_port))

            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.bind(('0.0.0.0', 0))
            px.sendall(remote.getsockname()[1].to_bytes(2, 'big'))

            # wait for client to ready for a connection
            signal = px.recv(2)
            assert signal == b'\x00\x00', signal

            remote.connect(remote_dst_addr)

            with px_lock:
                rlist.append(proxy)
                rlist.append(remote)
                proxy_conns[proxy] = remote
                remote_conns[remote] = proxy


    Thread(target=px_thread).start()

    try:
        while True:
            for s in select.select(rlist, [], [], 1)[0]:
                with px_lock:
                    if s in proxy_conns:
                        conns1, conns2 = proxy_conns, remote_conns
                    elif s in remote_conns:
                        conns1, conns2 = remote_conns, proxy_conns
                    else:
                        assert False, s

                    try:
                        data = s.recv(4096)
                        conns1[s].sendall(data)
                    except ConnectionResetError:
                        print('ConnectionResetError:', s)
                        data = ''
                    except BrokenPipeError:
                        print('BrokenPipeError:', s)
                        data = ''

                    if not data:
                        print('close/remove:', s)
                        s.close()
                        rlist.remove(s)
                        print('close/remove:', conns1[s])
                        conns1[s].close()
                        rlist.remove(conns1[s])
                        del conns2[conns1[s]]
                        del conns1[s]
                        break
    finally:
        mitm.terminate()
        px.close()
        for s in rlist:
            s.close()

        print()
        print('Connection Terminated')


if __name__ == '__main__':
    exit(main())
