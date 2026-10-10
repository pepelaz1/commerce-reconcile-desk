"""Local demonstration server, using only the Python standard library."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
from reconcile import reconcile, export_csv

ROOT = Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
    def respond(self, status, content, mime):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(content.encode('utf8'))
    def do_GET(self):
        if self.path == '/':
            self.respond(200, (ROOT/'index.html').read_text(encoding='utf8'), 'text/html; charset=utf-8')
        elif self.path == '/api/sample':
            self.respond(200, json.dumps({k: (ROOT/'samples'/f'{k}.csv').read_text(encoding='utf8') for k in ['orders','payments']}), 'application/json')
        else:
            self.respond(404, 'Not found', 'text/plain')
    def do_POST(self):
        if self.path not in ['/api/reconcile', '/api/export']:
            return self.respond(404, 'Not found', 'text/plain')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size <= 0 or size > 1_000_000:
                raise ValueError('Request must contain JSON below 1 MB')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict) or not all(isinstance(data.get(k),str) for k in ['orders','payments']):
                raise ValueError('orders and payments must be CSV strings')
            result = reconcile(data['orders'], data['payments'])
            if self.path == '/api/export':
                self.respond(200, export_csv(result), 'text/csv; charset=utf-8')
            else:
                self.respond(200, json.dumps(result), 'application/json')
        except (ValueError, KeyError, UnicodeDecodeError) as error:
            self.respond(400, json.dumps({'error':str(error)}), 'application/json')

if __name__ == '__main__':
    print('Commerce Reconcile Desk: http://127.0.0.1:8768', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8768), Handler).serve_forever()
