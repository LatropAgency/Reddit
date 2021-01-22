import argparse
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import re
from logger_conf import configurate_logger
from threading import Timer

from validators import logmode_validator, unsigned_int_validator

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


class Storage:
    def __init__(self, keys, cooldown):
        self.keys = keys
        self.items = self.get_all()
        self.cooldown = cooldown
        self.save()

    def get_all(self):
        filename = f'{datetime.today().strftime("reddit-%Y%m%d")}.txt'
        mode = 'r' if os.path.exists(filename) else 'w+'
        with open(filename, mode) as f:
            items = [line.split(';') for line in f.read().split('\n') if line != '']
        return {item[0]: dict(zip(self.keys, item)) for item in items}

    def save(self):
        for i in threading.enumerate():
            if i.name == "MainThread":
                break
        else:
            return
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
        super(BaseHTTPRequestHandler, self).__init__(*args, **kwargs)

    def set_headers(self, status_code):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def unknown_resourse(self, unique_id):
        logging.debug(f'Unknown resource with UNIQUE_ID: {unique_id}')
        self.set_headers(404)

    def default_route(self):
        self.set_headers(200)

    def get_all_posts(self):
        self.set_headers(200)
        self.wfile.write(bytes(json.dumps(list(HttpHandler.storage.items.values())), 'utf-8'))

    def get_post_from_body(self):
        length = int(self.headers.get('Content-Length'))
        body = self.rfile.read(length).decode('utf-8')
        return json.loads(body)

    def insert_post(self):
        post = self.get_post_from_body()
        HttpHandler.storage.insert(post, post['unique_id'])
        self.set_headers(201)
        self.wfile.write(
            bytes(json.dumps({post['unique_id']: list(HttpHandler.storage.items.keys()).index(post['unique_id'])}),
                  'utf-8'))

    def delete_post(self):
        unique_id = self.path.split('/')[2]
        if unique_id not in HttpHandler.storage.items.keys():
            self.unknown_resourse(unique_id)
        else:
            self.set_headers(200)
            logging.debug(f'Post with UNIQUE_ID: {unique_id} is deleted')
            HttpHandler.storage.delete(unique_id)

    def get_post(self):
        unique_id = self.path.split('/')[2]
        post = HttpHandler.storage.get_by_id(unique_id)
        if not post:
            self.unknown_resourse(unique_id)
        else:
            self.set_headers(200)
            self.wfile.write(bytes(json.dumps(post), 'utf-8'))

    def update_post(self):
        unique_id = self.path.split('/')[2]
        if not HttpHandler.storage.get_by_id(unique_id):
            self.unknown_resourse(unique_id)
        else:
            logging.debug(f'Updated post with UNIQUE_ID: {unique_id}')
            post = self.get_post_from_body()
            HttpHandler.storage.update(unique_id, post)
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
    parser.add_argument('-p', '--port', required=False, default=8087, type=unsigned_int_validator,
                        help='Port of HTTP server')
    parser.add_argument('-c', '--cooldown', required=False, default=10, type=unsigned_int_validator,
                        help='Autosave cooldown')
    parser.add_argument('--logmode',
                        required=False,
                        default='ALL',
                        type=logmode_validator,
                        help="""Log mode  
                                - ALL - all levers, 
                                ERROR - only ERROR lever, 
                                WARNING - only WARNING lever, 
                                DISABLE - no console console log""")
    args = parser.parse_args()

    configurate_logger(args.logmode)
    logging.debug(f'Server started http://{HOSTNAME}:{args.port}')

    HttpHandler.storage = Storage(KEYS, args.cooldown)
    server = HTTPServer((HOSTNAME, args.port), HttpHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        logging.debug("Server stopped.")
