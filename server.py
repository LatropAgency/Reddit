import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import re
import os
from threading import Timer

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


class HttpServer:
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
        self.router = {
            'GET': {
                r'^/posts/$': self.get_all_posts,
                r'^/posts/[a-z0-9-]{36}/$': self.get_post,
            },
            'POST': {
                r'^/posts/$': self.insert_post,
            },
            'DELETE': {
                r'^/posts/[a-z0-9-]{36}/$': self.delete_post
            },
            'PUT': {
                r'^/posts/[a-z0-9-]{36}/$': self.update_post
            },
            'DEFAULT': self.default_route,
        }
        self.storage = self.__class__.storage
        super(BaseHTTPRequestHandler, self).__init__(*args, **kwargs)

    def set_headers(self, status_code):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def default_route(self):
        self.set_headers(200)

    def get_all_posts(self):
        self.set_headers(200)
        self.wfile.write(bytes(json.dumps(list(self.storage.items.values())), 'utf-8'))

    def get_post_from_body(self):
        length = int(self.headers.get('Content-Length'))
        body = self.rfile.read(length).decode('utf-8')
        return json.loads(body)

    def insert_post(self):
        post = self.get_post_from_body()
        self.storage.insert(post, post['unique_id'])
        self.set_headers(201)
        self.wfile.write(
            bytes(json.dumps({post['unique_id']: list(self.storage.items.keys()).index(post['unique_id'])}),
                  'utf-8'))

    def delete_post(self):
        unique_id = self.path.split('/')[2]
        if unique_id not in self.storage.items.keys():
            self.set_headers(404)
        else:
            self.set_headers(200)
            self.storage.delete(unique_id)

    def get_post(self):
        unique_id = self.path.split('/')[2]
        post = self.storage.get_by_id(unique_id)
        if not post:
            self.set_headers(404)
        else:
            self.set_headers(200)
            self.wfile.write(bytes(json.dumps(post), 'utf-8'))

    def update_post(self):
        unique_id = self.path.split('/')[2]
        if not self.storage.get_by_id(unique_id):
            self.set_headers(404)
        else:
            post = self.get_post_from_body()
            self.storage.update(unique_id, post)
            self.set_headers(200)

    def find_route(self, method):
        for route in self.router[method].keys():
            if re.match(route, self.path):
                return self.router[method][route]()
        return self.router['DEFAULT']()

    def do_GET(self):
        self.find_route('GET')

    def do_POST(self):
        self.find_route('POST')

    def do_DELETE(self):
        self.find_route('DELETE')

    def do_PUT(self):
        self.find_route('PUT')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Reddit parser')
    parser.add_argument('-p', '--port', required=False, default=8087, type=unsigned_int_validator, help='Port of HTTP server')
    parser.add_argument('-c', '--cooldown', required=False, default=10, type=unsigned_int_validator, help='Autosave cooldown')
    args = parser.parse_args()

    HttpServer(HOSTNAME, args.port, Storage(KEYS, args.cooldown))
