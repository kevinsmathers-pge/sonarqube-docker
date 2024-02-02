from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl


def certIsValid(cert):
    kv = cert['subjectAltName'][0]
    #print(kv)
    key,val = kv
    if key != 'DNS' or val != 'mtls-client.domain.com':
        return False
    kv = cert['issuer'][5][0]
    key,val = kv
    if key != 'commonName' or val != 'mtls-server.domain.com':
        return False
    return True

class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"GET {self.path}")
        if self.path.startswith("/secret/"):
            import keyring
            args = self.path.split("/")
            secret = None
            if len(args) == 4:
                service = args[2]
                user = args[3]
                secret = keyring.get_password(service, user)
            if secret is None:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(bytes(f'Unknown secret {service} {user}', 'UTF-8'))
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(secret, 'UTF-8'))
        elif self.path.startswith("/foundry-token"):
            import foundrysmith as fsm
            import json
            api = fsm.FoundryAPI()
            token_data = { "token": api.auth_token }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            print("send> '{json.dumps(token_data)}")
            self.wfile.write(bytes(json.dumps(token_data), 'UTF-8'))
        else:
            # cert = self.connection.getpeercert()
            # if cert is None or not certIsValid(cert):
            #     self.send_response(403)
            #     self.end_headers()
            #     return

            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(bytes('Unrecognized request {self.path}', 'UTF-8'))


def certpath(name, ext):
    return f"./openssl/{name}/{name}.{ext}"

def certpair(name):
    return (certpath(name, "crt"), certpath(name, "key"))

httpd = HTTPServer(('localhost', 4443), MyHTTPRequestHandler)

#httpd.socket = ssl.wrap_socket (httpd.socket,
#        keyfile=certpath("mtls-server.domain.com", "key"),
#        certfile=certpath("mtls-server.domain.com", "crt"),
#        ca_certs="./openssl/certs/myCA.pem", server_side=True, cert_reqs=ssl.CERT_REQUIRED)


print("listening at localhost:4443")
httpd.serve_forever()
