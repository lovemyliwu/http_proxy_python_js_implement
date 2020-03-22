import http.server
import selectors
import socketserver
import socket

PORT = 8888
tunnel_map = {}
ip_info = {}
selector = selectors.DefaultSelector()

class Handler(http.server.BaseHTTPRequestHandler):
    def shutdown_tunnel(self, one_connection):
        try:
            selector.unregister(one_connection)
        except:
            pass
        try:
            selector.unregister(tunnel_map[one_connection])
        except:
            pass

        self.server.shutdown_request(one_connection)
        self.server.shutdown_request(tunnel_map[one_connection])

    def data_ready(self, connection, ip):
        try:
            data = connection.recv(10240)
        except Exception as e:
            print(f'shutdown tunnel due to read data from ip:{ip} error:{e}')
            self.shutdown_tunnel(connection)
            return

        if not data:
            return

        target_ip = ip_info[tunnel_map[connection]]
        print(f'tunnel recv {len(data)} bytes from ip:{ip} redirect to ip:{target_ip}')

        try:
            tunnel_map[connection].send(data)
        except Exception as e:
            print(f'shutdown tunnel due to write data to ip:{target_ip} error:{e}')
            self.shutdown_tunnel(connection)


    def handle(self):
        self.raw_requestline = self.rfile.readline()
        ok = self.parse_request()
        if not ok:
            raise Exception(f'request incorrect, shutdown connection')

        print(f'{self.command} {self.path}')

        if self.request not in tunnel_map:
            self.handle_new_client()
        else:
            self.data_ready(self.request, self.client_address)

    def handle_new_client(self):
        if self.command != 'CONNECT':
            raise Exception(f'tunnel not ready, shutdown connection')

        print(f'make tunnel to:{self.path} for client:{self.client_address}')
        host, port = self.path.split(':')
        destination = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        destination.connect((host, int(port)))
        destination_ip, _ = destination.getpeername()

        tunnel_map[self.request] = destination
        tunnel_map[destination] = self.request

        ip_info[self.request] = self.client_address
        ip_info[destination] = destination_ip

        selector.register(destination, selectors.EVENT_READ, self.data_ready)
        selector.register(self.request, selectors.EVENT_READ, self.data_ready)

        self.request.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')


class Server(socketserver.TCPServer):
    def process_request(self, request, client_address):
        self.finish_request(request, client_address)
        # override to disable shutdown request after process request
        # self.shutdown_request(request)

    def service_actions(self):
        events = selector.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, ip_info[key.fileobj])


with Server(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
