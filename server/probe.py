"""Temporary test server (Railway): can this server's address reach Instagram, TikTok and YouTube?
It only looks links up (no media is downloaded) and switches itself off 48 hours after it starts.

POST /probe {"urls": [...], "gap": seconds}  ->  [{url, ok, seconds, title, formats, pictures, error}]
"""
import os, json, time, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

STARTED = time.time()
LIFETIME = 48 * 3600
LOCK = threading.Lock()


def look(url):
    from yt_dlp import YoutubeDL
    t = time.time()
    opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'ignore_no_formats_error': 'instagram.com' in url,
            'noplaylist': True, 'socket_timeout': 30, 'remote_components': ['ejs:github']}
    if os.path.exists('/usr/local/bin/deno'):
        opts['js_runtimes'] = {'deno': {'path': '/usr/local/bin/deno'}}
    try:
        with YoutubeDL(opts) as y:
            info = y.extract_info(url, download=False)
        entries = [e for e in (info.get('entries') or [info]) if e]
        return {'url': url, 'ok': True, 'seconds': round(time.time() - t, 1), 'title': (info.get('title') or '')[:80],
                'formats': sum(1 for e in entries if e.get('formats')), 'pictures': sum(1 for e in entries if not e.get('formats') and e.get('thumbnails'))}
    except Exception as e:
        return {'url': url, 'ok': False, 'seconds': round(time.time() - t, 1), 'error': str(e)[:300]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/healthz':
            from yt_dlp.version import __version__
            return self.send(200, {'ok': True, 'yt_dlp': __version__, 'deno': os.path.exists('/usr/local/bin/deno'),
                                   'hours_left': round((LIFETIME - (time.time() - STARTED)) / 3600, 1)})
        self.send(404, {'error': 'not found'})

    def do_POST(self):
        if time.time() - STARTED > LIFETIME:
            return self.send(410, {'error': 'this test server has ended'})
        if self.path != '/probe':
            return self.send(404, {'error': 'not found'})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get('Content-Length') or 0), 100_000)) or b'{}')
        except ValueError:
            return self.send(400, {'error': 'bad json'})
        urls = [u for u in body.get('urls', []) if isinstance(u, str) and u.startswith('https://')][:15]
        gap = min(max(float(body.get('gap', 2)), 0), 10)
        if not LOCK.acquire(blocking=False):
            return self.send(429, {'error': 'one test at a time'})
        try:
            out = []
            for i, u in enumerate(urls):
                if i:
                    time.sleep(gap)
                out.append(look(u))
            return self.send(200, out)
        finally:
            LOCK.release()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    print('probe on', port, flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()
