import base64
import http.server
import socketserver
from http import HTTPStatus

import requests

PORT = 8888

class Handler(http.server.BaseHTTPRequestHandler):
    def return_407(self):
        self.send_response(HTTPStatus.PROXY_AUTHENTICATION_REQUIRED)
        self.send_header('Proxy-Authenticate', 'Basic realm="demo proxy"')
        self.end_headers()

    def validate(self, credential):
        try:
            credential = credential.split(' ')[1]
            credential = base64.b64decode(credential.encode()).decode()
            username, password = credential.split(':')
            return username == 'test' and password == 'testme'
        except:
            return False

    def do_GET(self):
        credential = self.headers.get('Proxy-Authorization')
        if credential is None or not self.validate(credential):
            self.return_407()
        print(f'proxy for:{self.path}')
        response = requests.get(self.path, stream=True)
        for chunk in response.iter_content(chunk_size=128):
            self.wfile.write(chunk)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
