import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import re
import os
from threading import Thread, Timer

from validators import unsigned_int_validator

HOSTNAME = 'localhost'
KEYS = ['unique_id',
        'url',
        'username',
        'user_karma',
        'cake-day',
        'post_karma',
        'comment_karma',
        'post_date',
        'comment_count',
        'count_votes',
        'category',
        ]


class http_server:
    def __init__(self, hostname, port, storage):
        HttpHandler.storage = storage
        server = HTTPServer((hostname, port), HttpHandler)
        server.serve_forever()


class Storage:
    def __init__(self, keys, cooldown):
        self.keys = keys
        self.items = self.get_all()
        self.cooldown = cooldown
        self.save()

    def get_all(self):
        filename = f'{datetime.today().strftime("reddit-%Y%m%d")}.txt'
        if not os.path.exists(filename):
            with open(filename, 'w'):
                pass
        with open(filename, 'r') as f:
            items = [line.split(';') for line in f.read().split('\n') if line != '']
        return {item[0]: dict(zip(self.keys, item)) for item in items}

    def save(self):
        with open(f'{datetime.today().strftime("reddit-%Y%m%d")}.txt', "w") as file:
            file.writelines([';'.join(item.values()) + '\n' for item in self.items.values()])
        Timer(self.cooldown, self.save).start()

    def get_by_id(self, id):
        return self.items.get(id, None)

    def insert(self, item, id):
        self.items[id] = item

    def delete(self, id):
        del self.items[id]

    def update(self, id, item):
        for key, value in item.items():
            self.items[id][key] = value


class HttpHandler(BaseHTTPRequestHandler):
    storage = None

    def __init__(self, *args, **kwargs):
        self.storage = self.__class__.storage
        super(BaseHTTPRequestHandler, self).__init__(*args, **kwargs)

    def _set_headers(self, status_code):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_GET(self):
        if self.path == '/posts/':
            self._set_headers(200)
            self.wfile.write(bytes(json.dumps(list(self.storage.items.values())), 'utf-8'))
        elif re.match(r'/posts/[a-z0-9-]{36}/', self.path):
            unique_id = self.path.split('/')[2]
            post = self.storage.get_by_id(unique_id)
            if post:
                self._set_headers(200)
                self.wfile.write(bytes(json.dumps(post), 'utf-8'))
            else:
                self._set_headers(404)
        else:
            self._set_headers(200)

    def do_POST(self):
        if self.path != '/posts/':
            self._set_headers(200)
        else:
            length = int(self.headers.get('Content-Length'))
            body = self.rfile.read(length).decode('utf-8')
            post = json.loads(body)
            self.storage.insert(post, post['unique_id'])
            self._set_headers(201)
            self.wfile.write(
                bytes(json.dumps({post['unique_id']: list(self.storage.items.keys()).index(post['unique_id'])}),
                      'utf-8'))

    def do_DELETE(self):
        if not re.match(r'/posts/[a-z0-9-]{36}/', self.path):
            self._set_headers(404)
        else:
            unique_id = self.path.split('/')[2]
            if unique_id in self.storage.items.keys():
                self._set_headers(200)
                self.storage.delete(unique_id)
            else:
                self._set_headers(404)

    def do_PUT(self):
        if not re.match(r'/posts/[a-z0-9-]{36}/', self.path):
            self._set_headers(404)
        else:
            unique_id = self.path.split('/')[2]
            length = int(self.headers.get('Content-Length'))
            body = self.rfile.read(length).decode('utf-8')
            post = json.loads(body)
            self.storage.update(unique_id, post)
            self._set_headers(200)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Reddit parser')
    parser.add_argument('port', type=unsigned_int_validator, help='Port of HTTP server')
    parser.add_argument('--cooldown', required=False, default=10, type=unsigned_int_validator, help='Autosave cooldown')
    args = parser.parse_args()

    http_server(HOSTNAME, args.port, Storage(KEYS, args.cooldown))
