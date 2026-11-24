"""Bulk Media Downloader on the web (Railway): the website sends links here, this server downloads them, packs a ZIP
and hands back download links. Files are kept for one hour.

    POST /api/jobs        {"text": "...links...", "quality": "best|720|audio"}  ->  {"id": ...}
    GET  /api/jobs/<id>                                                          ->  progress, files, ZIP
    GET  /files/<id>/<n>  /files/<id>/zip                                        ->  the file (when there is no storage bucket)

With a storage bucket (S3-compatible, e.g. a Railway bucket) the files go there and visitors download them straight
from the bucket. Without one, this server sends them itself.
"""
import os, re, json, time, uuid, shutil, threading, mimetypes
from collections import defaultdict, deque
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, quote

import engine

MAX_LINKS = int(os.environ.get('MAX_LINKS', '30'))
KEEP = int(os.environ.get('KEEP_SECONDS', '3600'))                     # files are deleted after this
LINKS_PER_HOUR = int(os.environ.get('LINKS_PER_HOUR', '120'))          # per visitor address
WORK = os.environ.get('WORK_DIR', '/tmp/bmd')
ORIGINS = {o.strip() for o in os.environ.get('ALLOWED_ORIGINS', 'https://bulkmediadownloader.com,https://www.bulkmediadownloader.com').split(',') if o.strip()}
QUALITY = {'best': '1080', '720': '720', 'audio': 'audio'}               # on the web "best" means up to 1080p (4K is for the app)
engine.EXTRA_OPTS.update({'max_filesize': 1_500_000_000,
                          'match_filter': lambda info, incomplete=False: 'This video is longer than 3 hours; use the Windows app for it.'
                          if (info.get('duration') or 0) > 3 * 3600 else None})
RETRY_AFTER = [60, 180]                                                  # a site that limits us: try again after 1, then 3 minutes
BUSY_WORDS = ('limiting downloads', 'not a bot')

JOBS = {}
LOCK = threading.Lock()
SEEN = defaultdict(deque)        # visitor address -> times of their links in the last hour
QUEUE = {'instagram': deque(), 'other': deque()}
WAKE = threading.Condition()


# ------------------------------------------------------------------ storage
def _env(*names):
    return next((os.environ[n] for n in names if os.environ.get(n)), None)


BUCKET = _env('BUCKET', 'S3_BUCKET', 'BUCKET_NAME', 'AWS_S3_BUCKET_NAME')
_s3 = None
if BUCKET:
    import boto3
    from botocore.config import Config
    _s3 = boto3.client('s3', endpoint_url=_env('ENDPOINT', 'S3_ENDPOINT', 'AWS_ENDPOINT_URL', 'AWS_ENDPOINT_URL_S3'),
                       region_name=_env('REGION', 'S3_REGION', 'AWS_REGION', 'AWS_DEFAULT_REGION') or 'auto',
                       aws_access_key_id=_env('ACCESS_KEY_ID', 'S3_ACCESS_KEY_ID', 'AWS_ACCESS_KEY_ID'),
                       aws_secret_access_key=_env('SECRET_ACCESS_KEY', 'S3_SECRET_ACCESS_KEY', 'AWS_SECRET_ACCESS_KEY'),
                       config=Config(signature_version='s3v4', s3={'addressing_style': 'path' if os.environ.get('S3_PATH_STYLE') else 'virtual'}))


def _put(path, key):
    _s3.upload_file(path, BUCKET, key, ExtraArgs={'ContentType': mimetypes.guess_type(path)[0] or 'application/octet-stream'})


def _link(key, name):
    return _s3.generate_presigned_url('get_object', ExpiresIn=KEEP, Params={
        'Bucket': BUCKET, 'Key': key, 'ResponseContentDisposition': f"attachment; filename*=UTF-8''{quote(name)}"})


def _delete_prefix(prefix):
    if not _s3:
        return
    try:
        keys = [o['Key'] for o in _s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix).get('Contents', [])]
        if keys:
            _s3.delete_objects(Bucket=BUCKET, Delete={'Objects': [{'Key': k} for k in keys]})
    except Exception as e:
        print('bucket delete:', prefix, e, flush=True)


# ------------------------------------------------------------------ jobs
def new_job(text, quality, who):
    links = engine.links_in(text)
    if not links:
        raise ValueError('No links found. Paste links that start with https://')
    if len(links) > MAX_LINKS:
        raise ValueError(f'Up to {MAX_LINKS} links at once on the website. Split them into smaller batches, or use the Windows app for up to 100.')
    now = time.time()
    with LOCK:
        seen = SEEN[who]
        while seen and now - seen[0] > 3600:
            seen.popleft()
        if len(seen) + len(links) > LINKS_PER_HOUR:
            raise PermissionError(f'You reached {LINKS_PER_HOUR} links per hour. Please wait a bit, or use the free Windows app for big batches.')
        seen.extend([now] * len(links))
        jid = uuid.uuid4().hex[:16]
        folder = os.path.join(WORK, jid)
        os.makedirs(folder)
        job = {'id': jid, 'created': now, 'expires': now + KEEP, 'quality': quality, 'folder': folder, 'done': False,
               'zip': None, 'zip_error': None,
               'items': [{'n': i, 'url': u, 'platform': engine.platform(u), 'state': 'waiting', 'percent': 0, 'title': '',
                          'files': [], 'links': [], 'error': '', 'tries': 0, 'not_before': 0} for i, u in enumerate(links)]}
        JOBS[jid] = job
        for it in job['items']:
            QUEUE['instagram' if it['platform'] == 'instagram' else 'other'].append((jid, it['n']))
    with WAKE:
        WAKE.notify_all()
    return jid


def _next(kind):
    """The next item of this kind that may run now (items waiting for a retry stay in line)."""
    with LOCK:
        q = QUEUE[kind]
        for _ in range(len(q)):
            jid, n = q.popleft()
            job = JOBS.get(jid)
            if not job:
                continue
            it = job['items'][n]
            if it['not_before'] > time.time():
                q.append((jid, n))
                continue
            return job, it
    return None


def worker(kind):
    while True:
        got = _next(kind)
        if not got:
            with WAKE:
                WAKE.wait(5)
            continue
        job, it = got
        it['state'], it['error'] = 'working', ''
        sub = os.path.join(job['folder'], f"{it['n'] + 1:02d}")
        os.makedirs(sub, exist_ok=True)
        try:
            if kind == 'instagram':
                time.sleep(1.5)
            engine._download(it, QUALITY[job['quality']], sub)
            if not it['files']:
                raise RuntimeError(it['error'] or 'Nothing to download was found in this post.')
            it['state'], it['percent'], it['error'] = 'done', 100, ''
        except Exception as e:
            msg = engine.friendly(e)
            if any(w in msg for w in BUSY_WORDS) and it['tries'] < len(RETRY_AFTER):
                it['not_before'] = time.time() + RETRY_AFTER[it['tries']]
                it['tries'] += 1
                it['state'], it['error'] = 'waiting', 'The site is busy; trying again in a minute.'
                with LOCK:
                    QUEUE[kind].append((job['id'], it['n']))
                continue
            it['state'], it['error'], it['files'] = 'failed', msg, []
            print('failed:', it['url'], '->', str(e)[:300], flush=True)
        _finish_if_done(job)


def _finish_if_done(job):
    with LOCK:
        if job['done'] or any(i['state'] in ('waiting', 'working') for i in job['items']):
            return
        job['done'] = 'packing'
    try:
        _publish(job)
    except Exception as e:
        job['zip_error'] = 'The files could not be prepared for download. Please try again.'
        print('publish:', job['id'], e, flush=True)
    job['done'] = True


def _publish(job):
    """Every file under a short name, plus one ZIP with all of them; into the bucket when there is one."""
    files = [(it, f) for it in job['items'] if it['state'] == 'done' for f in it['files'] if os.path.isfile(f)]
    if not files:
        return
    names, used = [], set()
    for it, f in files:
        name = os.path.basename(f)
        base, ext = os.path.splitext(name)
        k = 2
        while name.lower() in used:
            name = f'{base} ({k}){ext}'
            k += 1
        used.add(name.lower())
        names.append((it, f, name))
    zip_path = os.path.join(job['folder'], 'Bulk Media Downloader.zip')
    import zipfile
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
        for _, f, name in names:
            z.write(f, name)
    zip_name = f"Bulk Media Downloader {time.strftime('%Y-%m-%d %H-%M', time.gmtime(job['created']))}.zip"
    for idx, (it, f, name) in enumerate(names):
        size = os.path.getsize(f)
        if _s3:
            key = f"{job['id']}/{idx}{os.path.splitext(name)[1]}"
            _put(f, key)
            it['links'].append({'name': name, 'size': size, 'url': _link(key, name)})
        else:
            it['links'].append({'name': name, 'size': size, 'url': f"/files/{job['id']}/{idx}"})
        job.setdefault('_paths', []).append(f)
    zsize = os.path.getsize(zip_path)
    if _s3:
        _put(zip_path, f"{job['id']}/all.zip")
        job['zip'] = {'name': zip_name, 'size': zsize, 'url': _link(f"{job['id']}/all.zip", zip_name)}
        shutil.rmtree(job['folder'], ignore_errors=True)       # everything is in the bucket now
    else:
        job['zip'] = {'name': zip_name, 'size': zsize, 'url': f"/files/{job['id']}/zip"}
        job['_zip_path'] = zip_path


def janitor():
    """Deletes jobs, files and bucket objects after KEEP seconds."""
    while True:
        time.sleep(60)
        now = time.time()
        for jid, job in list(JOBS.items()):
            if now > job['expires']:
                with LOCK:
                    JOBS.pop(jid, None)
                shutil.rmtree(job['folder'], ignore_errors=True)
                _delete_prefix(jid + '/')


def public(job):
    return {'id': job['id'], 'done': job['done'] is True, 'expires': job['expires'], 'zip': job['zip'], 'zip_error': job['zip_error'],
            'items': [{k: it[k] for k in ('n', 'url', 'platform', 'state', 'percent', 'title', 'error', 'links')} for it in job['items']]}


# ------------------------------------------------------------------ http
class H(BaseHTTPRequestHandler):
    server_version = 'BMD'
    sys_version = ''

    def log_message(self, *a):
        pass

    def _cors(self):
        origin = self.headers.get('Origin', '')
        if origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Max-Age', '600')

    def send_json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def who(self):
        fwd = self.headers.get('X-Forwarded-For', '')
        return (fwd.split(',')[0].strip() if fwd else self.client_address[0]) or '?'

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/healthz':
            from yt_dlp.version import __version__
            return self.send_json(200, {'ok': True, 'yt_dlp': __version__, 'bucket': bool(_s3), 'jobs': len(JOBS)})
        m = re.fullmatch(r'/api/jobs/([0-9a-f]{16})', path)
        if m:
            job = JOBS.get(m.group(1))
            return self.send_json(200, public(job)) if job else self.send_json(404, {'error': 'This download has expired.'})
        m = re.fullmatch(r'/files/([0-9a-f]{16})/(zip|\d+)', path)
        if m:
            return self.send_file(m.group(1), m.group(2))
        return self.send_json(404, {'error': 'not found'})

    def send_file(self, jid, which):
        job = JOBS.get(jid)
        if not job or job['done'] is not True:
            return self.send_json(404, {'error': 'This download has expired.'})
        if which == 'zip':
            path, name = job.get('_zip_path'), (job['zip'] or {}).get('name', 'download.zip')
        else:
            paths = job.get('_paths') or []
            i = int(which)
            if i >= len(paths):
                return self.send_json(404, {'error': 'not found'})
            path = paths[i]
            name = next((l['name'] for it in job['items'] for l in it['links'] if l['url'].endswith(f'/{i}')), os.path.basename(path))
        if not path or not os.path.isfile(path):
            return self.send_json(404, {'error': 'This download has expired.'})
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(os.path.getsize(path)))
        self.send_header('Content-Disposition', f"attachment; filename*=UTF-8''{quote(name)}")
        self.end_headers()
        with open(path, 'rb') as f:
            shutil.copyfileobj(f, self.wfile, 1 << 20)

    def do_POST(self):
        if urlparse(self.path).path != '/api/jobs':
            return self.send_json(404, {'error': 'not found'})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get('Content-Length') or 0), 200_000)) or b'{}')
            quality = body.get('quality') if body.get('quality') in QUALITY else 'best'
            return self.send_json(200, {'id': new_job(str(body.get('text', '')), quality, self.who())})
        except PermissionError as e:
            return self.send_json(429, {'error': str(e)})
        except ValueError as e:
            return self.send_json(400, {'error': str(e)})


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    for kind, n in (('instagram', 1), ('other', int(os.environ.get('WORKERS', '3')))):
        for _ in range(n):
            threading.Thread(target=worker, args=(kind,), daemon=True).start()
    threading.Thread(target=janitor, daemon=True).start()
    port = int(os.environ.get('PORT', '8080'))
    print(f'web downloader on {port}; bucket: {BUCKET or "none (files served from here)"}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()


if __name__ == '__main__':
    main()
