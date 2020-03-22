import http.server
import socketserver

import requests

PORT = 8888

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(f'proxy for:{self.path}')
        response = requests.get(self.path, stream=True)
        for chunk in response.iter_content(chunk_size=128):
            self.wfile.write(chunk)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
