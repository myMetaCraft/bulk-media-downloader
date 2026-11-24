"""Bulk Media Downloader: a small local server on 127.0.0.1 and a window to it.

    pythonw bmd.py                 # the app (the Start menu shortcut)
    python bmd.py --no-window      # only the server; prints the address
    python bmd.py --smoke URL ...  # downloads the links into build/smoke and prints the result (the Windows build checks itself)

Installed layout: <install>/python  <install>/app (this file)  <install>/bin (ffmpeg, deno)
Data: %LOCALAPPDATA%\\Bulk Media Downloader (settings, log, fresher download engine).
"""
import os, sys, json, glob, time, socket, secrets, threading, subprocess
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALL = os.path.dirname(HERE)
NAME = 'Bulk Media Downloader'
WEBSITE = 'https://bulkmediadownloader.com'
VERSION = (open(os.path.join(INSTALL, 'VERSION')).read().strip() if os.path.isfile(os.path.join(INSTALL, 'VERSION')) else
           open(os.path.join(HERE, '..', 'VERSION')).read().strip() if os.path.isfile(os.path.join(HERE, '..', 'VERSION')) else '0.0.0')


def _home():
    base = os.environ.get('LOCALAPPDATA') or os.path.join(os.path.expanduser('~'), '.local', 'share')
    path = os.path.join(base, NAME)
    os.makedirs(path, exist_ok=True)
    return path


HOME = _home()
sys.path.insert(0, HERE)
import updater                                           # noqa: E402
updater.activate(HOME)                                   # a fresher download engine, if one was fetched last time
bin_dir = os.path.join(INSTALL, 'bin')
if os.path.isdir(bin_dir):
    os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')
import engine                                            # noqa: E402

TOKEN = secrets.token_urlsafe(24)
SEEN = {'at': time.time()}


# ------------------------------------------------------------------ settings
def settings():
    try:
        s = json.load(open(os.path.join(HOME, 'settings.json')))
    except (OSError, ValueError):
        s = {}
    return {'folder': s.get('folder') or engine.default_folder(), 'quality': s.get('quality') if s.get('quality') in engine.QUALITIES else 'best',
            'zip': bool(s.get('zip', False))}


def save_settings(**kw):
    s = settings()
    s.update({k: v for k, v in kw.items() if v is not None})
    with open(os.path.join(HOME, 'settings.json'), 'w') as f:
        json.dump(s, f)


def choose_folder(start):
    """Windows' own folder picker (through PowerShell, so no extra library is needed). -> path or None"""
    if os.name != 'nt':
        return None
    ps = ('Add-Type -AssemblyName System.Windows.Forms;'
          '$f = New-Object System.Windows.Forms.FolderBrowserDialog;'
          '$f.Description = "Where should the downloads go?"; $f.ShowNewFolderButton = $true;'
          f'$f.SelectedPath = {json.dumps(start)};'
          '$w = New-Object System.Windows.Forms.Form; $w.TopMost = $true;'
          'if ($f.ShowDialog($w) -eq "OK") { [Console]::OutputEncoding = [Text.Encoding]::UTF8; $f.SelectedPath }')
    r = subprocess.run(['powershell', '-NoProfile', '-STA', '-Command', ps], capture_output=True, text=True, encoding='utf-8',
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    path = (r.stdout or '').strip()
    return path if path and os.path.isdir(path) else None


def reveal(path):
    if os.name == 'nt':
        if os.path.isfile(path):
            subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
        else:
            os.startfile(path)  # noqa: S606 (a folder the app made)
    else:
        subprocess.Popen(['xdg-open', path if os.path.isdir(path) else os.path.dirname(path)])


# ------------------------------------------------------------------ web
UI = open(os.path.join(HERE, 'ui.html'), encoding='utf-8').read()


class Handler(BaseHTTPRequestHandler):
    server_version = 'BMD'
    sys_version = ''

    def log_message(self, fmt, *args):
        pass

    def _host_ok(self):
        host = (self.headers.get('Host') or '').lower()
        return host in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def _send(self, code, body, ctype='application/json'):
        data = body if isinstance(body, bytes) else (json.dumps(body) if ctype == 'application/json' else body).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype + ('; charset=utf-8' if 'json' in ctype or 'html' in ctype else ''))
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        if 'html' in ctype:
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                                                        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        SEEN['at'] = time.time()
        if not self._host_ok():
            return self._send(403, {'error': 'wrong host'})
        path = urlparse(self.path).path
        if path == '/':
            return self._send(200, UI.replace('__TOKEN__', TOKEN).replace('__VERSION__', VERSION).replace('__WEBSITE__', WEBSITE), 'text/html')
        if path == '/healthz':
            return self._send(200, {'ok': True, 'app': NAME})
        if path == '/api/state':
            if self.headers.get('X-Token') != TOKEN:
                return self._send(403, {'error': 'wrong token'})
            return self._send(200, {'version': VERSION, 'engine': engine.engine_version(), 'settings': settings(),
                                    'qualities': engine.QUALITIES, 'batches': engine.snapshot(), 'max_links': engine.MAX_LINKS,
                                    'update': {'app_latest': updater.STATE['app_latest'], 'engine_installed': updater.STATE['installed']}})
        return self._send(404, {'error': 'not found'})

    def do_POST(self):
        SEEN['at'] = time.time()
        if not self._host_ok() or self.headers.get('X-Token') != TOKEN:
            return self._send(403, {'error': 'not allowed'})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get('Content-Length') or 0), 1_000_000)) or b'{}')
        except ValueError:
            return self._send(400, {'error': 'bad request'})
        path = urlparse(self.path).path
        try:
            if path == '/api/start':
                quality = body.get('quality') if body.get('quality') in engine.QUALITIES else 'best'
                folder = body.get('folder') or settings()['folder']
                save_settings(quality=quality, zip=bool(body.get('zip')), folder=folder)
                return self._send(200, {'batch': engine.start(body.get('text', ''), quality, folder, bool(body.get('zip')))})
            if path == '/api/retry':
                engine.retry(str(body.get('batch')), int(body.get('n', -1)))
                return self._send(200, {'ok': True})
            if path == '/api/folder':
                picked = choose_folder(settings()['folder'])
                if picked:
                    save_settings(folder=picked)
                return self._send(200, {'folder': settings()['folder']})
            if path == '/api/default-folder':
                save_settings(folder=engine.default_folder())
                return self._send(200, {'folder': settings()['folder']})
            if path == '/api/open':
                p = body.get('path') or ''
                if not engine.known_path(p) or not os.path.exists(p):
                    return self._send(404, {'error': 'That file or folder is not there any more.'})
                reveal(p)
                return self._send(200, {'ok': True})
            if path == '/api/clear':
                engine.forget_finished()
                return self._send(200, {'ok': True})
            if path == '/api/website':
                import webbrowser
                webbrowser.open(WEBSITE + str(body.get('page') or ''))
                return self._send(200, {'ok': True})
        except ValueError as e:
            return self._send(400, {'error': str(e)})
        return self._send(404, {'error': 'not found'})


# ------------------------------------------------------------------ window
def _free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _running():
    try:
        info = json.load(open(os.path.join(HOME, 'running.json')))
        import urllib.request
        body = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{info['port']}/healthz", timeout=2).read())
        return f"http://127.0.0.1:{info['port']}/" if body.get('app') == NAME else None
    except Exception:
        return None


def _browser():
    if os.name != 'nt':
        return None
    for base in (os.environ.get('ProgramFiles(x86)'), os.environ.get('ProgramFiles'), os.environ.get('LOCALAPPDATA')):
        if base:
            exe = os.path.join(base, 'Microsoft', 'Edge', 'Application', 'msedge.exe')
            if os.path.isfile(exe):
                return exe
    return None


def open_window(url):
    exe = _browser()
    if exe:
        try:
            return subprocess.Popen([exe, f'--app={url}', f'--user-data-dir={os.path.join(HOME, "window")}', '--no-first-run',
                                     '--no-default-browser-check', '--disable-features=Translate', '--window-size=1100,820'])
        except OSError as e:
            print('window:', e, flush=True)
    import webbrowser
    webbrowser.open(url)
    return None


def _window_open():
    """Is our window's profile still in use? (Edge can hand the window to another process)"""
    lock = os.path.join(HOME, 'window', 'lockfile')
    if not os.path.exists(lock):
        return False
    try:
        os.remove(lock)
        return False
    except PermissionError:
        return True
    except OSError:
        return False


WINDOW_GONE = 180


def _log_to_file():
    path = os.path.join(HOME, 'log.txt')
    try:
        if os.path.getsize(path) > 2_000_000:
            os.replace(path, path + '.old')
    except OSError:
        pass
    fh = open(path, 'a', buffering=1, encoding='utf-8', errors='replace')
    sys.stdout = sys.stderr = fh
    print(f'\n--- {NAME} {VERSION} starting {time.strftime("%Y-%m-%d %H:%M:%S")}', flush=True)


def smoke(links):
    """The build's self-check: download these links, print what happened, exit 0 only if every link worked."""
    out = os.path.join(os.getcwd(), 'build', 'smoke')
    bid = engine.start('\n'.join(links), 'best', out, True)
    while engine.busy():
        time.sleep(0.5)
    time.sleep(0.5)
    batch = [b for b in engine.snapshot() if b['id'] == bid][0]
    print(json.dumps({'engine': engine.engine_version(), 'zip': batch['zip_path'], 'items': [
        {k: i[k] for k in ('url', 'state', 'error', 'files')} for i in batch['items']]}, indent=1))
    return 0 if all(i['state'] == 'done' for i in batch['items']) and batch['zip_path'] else 1


def main(argv):
    if '--smoke' in argv:
        return smoke([a for a in argv if a.startswith('http')])
    if sys.executable.lower().endswith('pythonw.exe') or '--log' in argv:
        _log_to_file()
    url = _running()
    if url and '--no-window' not in argv:
        open_window(url)
        return 0
    port = _free_port()
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, name='http', daemon=True).start()
    url = f'http://127.0.0.1:{port}/'
    with open(os.path.join(HOME, 'running.json'), 'w') as f:
        json.dump({'port': port, 'pid': os.getpid()}, f)
    print(f'{NAME} is running at {url} (engine yt-dlp {engine.engine_version()})', flush=True)
    threading.Thread(target=updater.check, args=(HOME, VERSION), name='update', daemon=True).start()
    try:
        if '--no-window' in argv:
            while True:
                time.sleep(3600)
        win = open_window(url)
        while True:
            time.sleep(10)
            if win is not None and win.poll() is None:
                continue
            if _window_open() or time.time() - SEEN['at'] < WINDOW_GONE or engine.busy():
                continue
            return 0
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            os.remove(os.path.join(HOME, 'running.json'))
        except OSError:
            pass
        srv.shutdown()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
