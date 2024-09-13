from bs4 import BeautifulSoup
import requests

import time
import socket


RENTRY_URL_PREFIX = 'https://rentry.co/'
# RENTRY_URL_PREFIX = 'https://rentry.org/'  # alternative .org domain
IPV4_SERVICE_URL = 'https://ipinfo.io/ip'


class Rentry:
    def __init__(self, rentry_id, rentry_code):
        self.rentry_url = RENTRY_URL_PREFIX
        self.rentry_id = rentry_id
        self.rentry_code = rentry_code
        self.rentry_url_id = self.rentry_url + rentry_id

        self.session = requests.Session()
        self.session.headers['Referer'] = self.rentry_url_id
    
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()
        return False

    def _get_token(self):
        response = self.session.get(self.rentry_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.find('input', attrs={'name': 'csrfmiddlewaretoken'})['value']

    def get_raw(self):
        response = self.session.get(self.rentry_url_id + '/raw')
        response.raise_for_status()
        return response.text

    def edit_text(self, text):
        ''' maximum `text` length of 200,000 characters '''
        data = {
            'csrfmiddlewaretoken': self._get_token(),
            'text': text,
            'edit_code': self.rentry_code,
        }

        response = self.session.post(self.rentry_url_id + '/edit', data=data, allow_redirects=False)
        assert response.status_code == 302 and response.headers['Location'] == '/' + self.rentry_id, 'wrong edit_code?'


class PortExchangeHelper(Rentry):
    @staticmethod
    def _extract_addrs(text):
        addrs = []
        for addr in text.splitlines():
            ip, port = addr.split(':')
            addrs.append((ip, int(port)))
        return addrs

    @staticmethod
    def _addrs_to_text(addrs):
        text = ''
        for ip, port in addrs:
            text += f'{ip}:{port}\n'
        return text

    def get_public_ipv4(self):
        response = self.session.get(IPV4_SERVICE_URL)
        response.raise_for_status()
        return response.text
    
    def get(self):
        text = self.get_raw()
        return self._extract_addrs(text)

    def put(self, addrs):
        self.edit_text(self._addrs_to_text(addrs))

    def wait_empty(self, t=1):
        time.sleep(t)
        while self.get():
            time.sleep(t)
    
    def wait_check(self, addr, t=1):
        while True:
            time.sleep(t)
            addrs = self.get()
            assert len(addrs) in [1, 2], f'unexcepted addrs length, {addrs}'
            if len(addrs) == 2:
                return addrs
            assert addrs[0] == addr, 'race condition detected!'

    def put_one_wait_two(self, addr, t=1):
        self.put([addr])
        addrs = self.wait_check(addr, t)
        assert addrs[0] == addr, f'unexpected addrs order, {addrs}'
        return addrs[1]  # returns the new/dst addr


def get_avail_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]
