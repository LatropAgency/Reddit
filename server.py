import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import re

HOSTNAME = 'localhost'
PORT = 8087
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


class Server(BaseHTTPRequestHandler):
    def _set_headers(self, status_code):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def _get_all_posts(self):
        with open(f'{datetime.today().strftime("reddit-%Y%m%d")}.txt', 'r') as f:
            posts = [line.split(';') for line in f.read().split('\n')]
        return {post[0]: dict(zip(KEYS, post)) for post in posts}

    def _get_post(self, unique_id):
        posts = self._get_all_posts()
        return posts.get(unique_id, None)

    def _save(self, posts):
        with open(f'{datetime.today().strftime("reddit-%Y%m%d")}.txt', "w") as file:
            file.writelines([';'.join(post.values()) + '\n' for post in posts.values()])

    def _append(self, post):
        with open(f'{datetime.today().strftime("reddit-%Y%m%d")}.txt', 'a+') as f:
            f.write('\n' + ';'.join(post.values()))

    def do_GET(self):
        if (self.path == '/posts/'):
            posts = self._get_all_posts()
            self._set_headers(200)
            self.wfile.write(bytes(json.dumps(list(posts.values())), 'utf-8'))
        elif re.match(r'/posts/[a-z0-9-]{36}/', self.path):
            unique_id = self.path.split('/')[2]
            post = self._get_post(unique_id)
            if post:
                self._set_headers(200)
                self.wfile.write(bytes(json.dumps(post), 'utf-8'))
            else:
                self._set_headers(404)
        else:
            self._set_headers(200)

    def do_POST(self):
        if (self.path == '/posts/'):
            length = int(self.headers.get('Content-Length'))
            body = self.rfile.read(length).decode('utf-8')
            post = json.loads(body)
            self._append(post)
            self._set_headers(201)
            self.wfile.write(bytes(json.dumps(post), 'utf-8'))
        else:
            self._set_headers(200)

    def do_DELETE(self):
        posts = self._get_all_posts()
        if re.match(r'/posts/[a-z0-9-]{36}/', self.path):
            unique_id = self.path.split('/')[2]
            del posts[unique_id]
            self._set_headers(200)
            self._save(posts)
        else:
            self._set_headers(404)

    def do_PUT(self):
        posts = self._get_all_posts()
        if re.match(r'/posts/[a-z0-9-]{36}/', self.path):
            unique_id = self.path.split('/')[2]
            length = int(self.headers.get('Content-Length'))
            body = self.rfile.read(length).decode('utf-8')
            post = json.loads(body)
            for key, value in post.items():
                posts[unique_id][key] = value
            self._set_headers(200)
            self._save(posts)
        else:
            self._set_headers(404)



if __name__ == "__main__":
    webServer = HTTPServer((HOSTNAME, PORT), Server)
    print("Server started http://%s:%s" % (HOSTNAME, PORT))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
