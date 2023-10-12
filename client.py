#!/usr/bin/python3

from helpers import PortExchangeHelper, get_avail_port

from threading import Thread, Lock
import socket
import select
import time
import sys


def tcp_punch(src_addr, dst_addr):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        s.bind(src_addr)
        src_addr_ = s.getsockname()
        
        s.settimeout(0.001)
        try:
            s.connect(dst_addr)  # punching
        except socket.timeout:
            pass

    return src_addr_


def accept_socket(src_addr, dst_addr, pre_accept=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(tcp_punch(src_addr, dst_addr))
        s.listen()
    except:
        s.close()
        raise
    if pre_accept:
        pre_accept()
    return s, s.accept()


def listen_socket(src_addr):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(src_addr)
        s.listen()
    except:
        s.close()
        raise
    return s


def estb_px(rentry_id, rentry_code):  # establish port exchange
    with PortExchangeHelper(rentry_id, rentry_code) as helper:
        port = get_avail_port()
        pub_addr = (helper.get_public_ipv4(), port)
        src_addr = ('', port)

        addrs = helper.get()
        if len(addrs) == 0:
            dst_addr = helper.put_one_wait_two(pub_addr)
            put_addrs = []
        elif len(addrs) == 1:
            dst_addr = addrs[0]
            put_addrs = addrs + [pub_addr]
        else:
            assert 0, f'unexcepted addrs length, {addrs}'
        
        return accept_socket(src_addr, dst_addr, lambda: helper.put(put_addrs))


def main():
    if len(sys.argv) in [3, 4]:
        rentry_id = sys.argv[1]
        rentry_code = sys.argv[2]
        proxy_port = int(sys.argv[3]) if len(sys.argv) == 4 else 0
    else:
        print('Usage:', sys.argv[0], 'rentry_id rentry_code [proxy_port]')
        return 1

    proxy_src_addr = ('127.0.0.1', proxy_port)  # local only
    # proxy_src_addr = ('0.0.0.0', proxy_port)  # all interfaces
    proxy = listen_socket(proxy_src_addr)
    print(':'.join(str(x) for x in proxy.getsockname()))

    remote = listen_socket(('0.0.0.0', 0))
    remote.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    remote_src_addr = remote.getsockname()
    remote_port_bytes = remote_src_addr[1].to_bytes(2, 'big')

    px, (px_conn, px_conn_addr) = estb_px(rentry_id, rentry_code)
    print('px_conn_addr:', px_conn_addr)
    px_conn.settimeout(10)

    rlist = []
    proxy_conns = {}
    remote_conns = {}
    pr_lock = Lock()  # proxy-remote lock
    pxkl_lock = Lock()  # port exchange keep-alive lock

    def proxy_remote():
        while True:
            proxy_conn, proxy_dst_addr = proxy.accept()
            print('proxy_dst_addr:', proxy_dst_addr)

            with pxkl_lock:
                px_conn.sendall(remote_port_bytes)
                port_bytes = px_conn.recv(2)
                assert port_bytes, 'port_bytes is empty'
                remote_dst_addr = px_conn_addr[0], int.from_bytes(port_bytes, 'big')
                tcp_punch(remote_src_addr, remote_dst_addr)
                px_conn.sendall(b'\x00\x00')

            remote_conn, remote_dst_addr_ = remote.accept()
            print('remote_dst_addr:', remote_dst_addr_)

            with pr_lock:
                rlist.append(proxy_conn)
                rlist.append(remote_conn)
                proxy_conns[proxy_conn] = remote_conn
                remote_conns[remote_conn] = proxy_conn


    def px_keepalive():
        while True:
            time.sleep(10)
            with pxkl_lock:
                px_conn.sendall(b'\x00\x00')


    Thread(target=proxy_remote).start()
    Thread(target=px_keepalive).start()

    try:
        while True:
            for s in select.select(rlist, [], [], 1)[0]:
                with pr_lock:
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
        proxy.close()
        remote.close()
        px_conn.close()
        px.close()

        print()
        print('Connection Terminated')


if __name__ == '__main__':
    exit(main())
