"""Downloads for Bulk Media Downloader.

Videos come through yt-dlp (Instagram, TikTok, YouTube and many more sites). Photos of Instagram posts come from the same
yt-dlp answer (the full-size picture of every slide); TikTok photo posts are read from the post's page.
Everything is fetched from the user's own connection, without logging in: only public posts.
"""
import os, re, json, time, zipfile, threading, itertools
from concurrent.futures import ThreadPoolExecutor

MAX_LINKS = 100
URL_RE = re.compile(r'https?://[^\s<>"\'`]+', re.I)
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

INSTALL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(INSTALL, 'bin')

QUALITIES = {
    'best': 'Best quality',
    '1080': 'Up to 1080p',
    '720': 'Up to 720p',
    'audio': 'Audio only (MP3)',
}

IMAGE_EXT = {'image/jpeg': '.jpg', 'image/jpg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/heic': '.heic', 'image/avif': '.avif'}
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'


# ------------------------------------------------------------------ links
def links_in(text):
    """Every link in the pasted text, once each, in order (at most MAX_LINKS)."""
    out, seen = [], set()
    for m in URL_RE.finditer(text or ''):
        url = m.group(0).rstrip('.,;:!?)]}>')
        key = url.split('#')[0]
        if key not in seen:
            seen.add(key)
            out.append(url)
    return out[:MAX_LINKS]


def platform(url):
    host = re.sub(r'^https?://', '', url.lower()).split('/')[0].split(':')[0]
    if host.endswith('instagram.com') or host == 'instagr.am':
        return 'instagram'
    if host.endswith('tiktok.com'):
        return 'tiktok'
    if host.endswith('youtube.com') or host.endswith('youtu.be') or host.endswith('youtube-nocookie.com'):
        return 'youtube'
    return 'other'


def friendly(msg):
    """yt-dlp's error -> one sentence a person understands."""
    msg = ANSI_RE.sub('', str(msg or '')).replace('ERROR: ', '').strip()
    m = msg.lower()
    if 'rate-limit' in m or 'rate limit' in m or 'too many requests' in m or ' 429' in m:
        return 'The site is limiting downloads right now. Wait a few minutes and retry this link.'
    if 'sign in to confirm' in m and 'bot' in m:
        return 'YouTube asked to confirm you are not a bot. Wait a while and retry this link.'
    if 'sign in to confirm your age' in m or 'age-restricted' in m or 'age restricted' in m:
        return 'This video is age-restricted, so it needs a login. Only public videos can be downloaded.'
    if 'empty media response' in m:
        return 'Instagram did not show this post to visitors who are not logged in (it may be private or age-restricted). Only public posts can be downloaded.'
    if 'private' in m or 'registered users' in m or 'logged-in' in m or 'logged in' in m or 'login required' in m or 'log in' in m or 'login' in m or 'cookies' in m:
        return 'This post is private or needs a login. Only public posts can be downloaded.'
    if 'unsupported url' in m:
        return 'This link is not supported. Use a link to a single post, reel or video.'
    if 'unavailable' in m or 'not available' in m or 'removed' in m or 'does not exist' in m or '404' in m:
        return 'This post is not available: deleted, private, or blocked in your country.'
    if 'no video' in m or 'no media' in m:
        return 'Nothing to download was found in this post.'
    if 'timed out' in m or 'connection' in m or 'network' in m or 'getaddrinfo' in m:
        return 'The connection failed. Check your internet and retry this link.'
    first = msg.splitlines()[0] if msg else 'Unknown error'
    return re.sub(r'^\[[^\]]+\]\s*[\w-]+:\s*', '', first)[:220]


# ------------------------------------------------------------------ folders
def downloads_dir():
    """The user's Downloads folder (wherever Windows keeps it)."""
    if os.name == 'nt':
        try:
            import ctypes, uuid
            from ctypes import wintypes
            guid = uuid.UUID('{374DE290-123F-4565-9164-39C4925E467B}')

            class GUID(ctypes.Structure):
                _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD), ('Data3', wintypes.WORD), ('Data4', wintypes.BYTE * 8)]
            g = GUID(guid.fields[0], guid.fields[1], guid.fields[2], (wintypes.BYTE * 8).from_buffer_copy(guid.bytes[8:]))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p)) == 0:
                path = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                if path and os.path.isdir(path):
                    return path
        except Exception:
            pass
    return os.path.join(os.path.expanduser('~'), 'Downloads')


def default_folder():
    return os.path.join(downloads_dir(), 'Bulk Media Downloader')


def _new_batch_folder(base):
    stamp = time.strftime('%Y-%m-%d %H-%M')
    path = os.path.join(base, stamp)
    for n in itertools.count(2):
        if not os.path.exists(path):
            break
        path = os.path.join(base, f'{stamp} ({n})')
    os.makedirs(path)
    return path


# ------------------------------------------------------------------ batches
BATCHES = {}
_LOCK = threading.Lock()
_ids = itertools.count(1)
_POOL = ThreadPoolExecutor(max_workers=3, thread_name_prefix='dl')
_INSTAGRAM = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ig')     # one Instagram post at a time: it limits anonymous visitors


def start(text, quality='best', folder=None, make_zip=False):
    """-> batch id; the downloads run in the background."""
    links = links_in(text)
    if not links:
        raise ValueError('No links found. Paste links that start with https://')
    quality = quality if quality in QUALITIES else 'best'
    base = folder or default_folder()
    os.makedirs(base, exist_ok=True)
    bid = str(next(_ids))
    batch = {'id': bid, 'created': time.time(), 'folder': _new_batch_folder(base), 'quality': quality, 'zip': bool(make_zip),
             'zip_path': None, 'zip_error': None, 'done': False,
             'items': [{'n': i, 'url': u, 'platform': platform(u), 'state': 'waiting', 'percent': 0, 'title': '', 'files': [], 'error': ''}
                       for i, u in enumerate(links)]}
    with _LOCK:
        BATCHES[bid] = batch
    for item in batch['items']:
        _queue(batch, item)
    return bid


def retry(bid, n):
    batch = BATCHES.get(bid)
    if not batch or not 0 <= n < len(batch['items']):
        raise ValueError('No such download')
    item = batch['items'][n]
    if item['state'] != 'failed':
        return
    item.update(state='waiting', percent=0, error='', files=[])
    batch['done'] = False
    _queue(batch, item)


def _queue(batch, item):
    pool = _INSTAGRAM if item['platform'] == 'instagram' else _POOL
    pool.submit(_run, batch, item)


def busy():
    return any(i['state'] in ('waiting', 'working') for b in list(BATCHES.values()) for i in b['items'])


def snapshot():
    with _LOCK:
        return [json.loads(json.dumps(b)) for b in sorted(BATCHES.values(), key=lambda b: -b['created'])]


def forget_finished():
    with _LOCK:
        for bid in [b['id'] for b in BATCHES.values() if b['done']]:
            BATCHES.pop(bid, None)


def known_path(path):
    """Is this a folder or file one of our batches made? (only those can be opened from the window)"""
    path = os.path.normcase(os.path.abspath(path))
    for b in BATCHES.values():
        roots = [b['folder']] + ([b['zip_path']] if b['zip_path'] else [])
        for r in roots:
            r = os.path.normcase(os.path.abspath(r))
            if path == r or path.startswith(r + os.sep):
                return True
    return False


def _run(batch, item):
    item['state'] = 'working'
    try:
        if item['platform'] == 'instagram':
            time.sleep(2)                               # gentle with Instagram: a short pause before each post
        _download(item, batch['quality'], batch['folder'])
        item['state'] = 'done' if item['files'] else 'failed'
        if item['files']:
            item['error'] = ''
        else:
            item['error'] = item['error'] or 'Nothing to download was found in this post.'
        item['percent'] = 100 if item['files'] else item['percent']
    except Exception as e:                              # one bad link never stops the others
        item['state'], item['error'] = 'failed', friendly(e)
        print('failed:', item['url'], '->', str(e)[:500], flush=True)
    finally:
        _finish_if_all_done(batch)


def _finish_if_all_done(batch):
    with _LOCK:
        if batch['done'] or any(i['state'] in ('waiting', 'working') for i in batch['items']):
            return
        batch['done'] = True
    if batch['zip'] and any(i['files'] for i in batch['items']):
        try:
            batch['zip_path'] = make_zip(batch['folder'])
        except Exception as e:
            batch['zip_error'] = f'The ZIP file could not be made: {e}'


def make_zip(folder):
    """All files of a batch in one ZIP next to its folder (stored, not compressed: videos do not get smaller)."""
    path = folder.rstrip('\\/') + '.zip'
    tmp = path + '.part'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, folder))
    os.replace(tmp, path)
    return path


# ------------------------------------------------------------------ one link
class _Log:
    def __init__(self, item):
        self.item = item

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.item['error'] = friendly(msg)


def _options(quality, folder, item, done_files):
    def progress(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            if total:
                item['percent'] = max(1, min(99, int(d.get('downloaded_bytes', 0) * 100 / total)))
        elif d.get('status') == 'finished' and d.get('filename'):
            done_files.append(d['filename'])
        info = d.get('info_dict') or {}
        if info.get('title') and not item['title']:
            item['title'] = str(info['title'])[:140]

    def after(d):
        if d.get('status') == 'finished':
            p = (d.get('info_dict') or {}).get('filepath')
            if p:
                done_files.append(p)

    opts = {
        'outtmpl': {'default': os.path.join(folder, '%(uploader,channel,creator,uploader_id|unknown).40B - %(title,description|post).60B [%(id)s].%(ext)s')},
        'windowsfilenames': True,
        'noplaylist': True,                 # a video link inside a playlist: only that video
        'playlist_items': '1:100',          # a playlist or a post with many slides: at most 100
        'ignore_no_formats_error': True,    # photo slides have no video: we take their pictures ourselves
        'quiet': True, 'no_warnings': True, 'noprogress': True,
        'logger': _Log(item),
        'progress_hooks': [progress], 'postprocessor_hooks': [after],
        'retries': 3, 'fragment_retries': 3, 'concurrent_fragment_downloads': 4,
        'socket_timeout': 30,
        'http_headers': {'User-Agent': UA},
        'remote_components': ['ejs:github'],   # YouTube's player puzzle solver, if the bundled one is out of date
    }
    if os.path.isfile(os.path.join(BIN, 'ffmpeg.exe')) or os.path.isfile(os.path.join(BIN, 'ffmpeg')):
        opts['ffmpeg_location'] = BIN
    deno = next((p for p in (os.path.join(BIN, 'deno.exe'), os.path.join(BIN, 'deno')) if os.path.isfile(p)), None)
    if deno:
        opts['js_runtimes'] = {'deno': {'path': deno}}
    if quality == 'audio':
        opts['format'] = 'ba/b'
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        opts['format'] = 'bv*+ba/b'
        opts['merge_output_format'] = 'mp4'
        opts['format_sort'] = {'best': ['res', 'ext:mp4:m4a'],
                               '1080': ['res:1080', 'vcodec:h264', 'ext:mp4:m4a'],
                               '720': ['res:720', 'vcodec:h264', 'ext:mp4:m4a']}[quality]
    return opts


def _entries(info):
    if not info:
        return []
    if info.get('_type') in ('playlist', 'multi_video') or info.get('entries') is not None:
        return [e for e in (info.get('entries') or []) if e]
    return [info]


def _download(item, quality, folder):
    """Look first, then fetch: every video slide through yt-dlp, every photo slide as its full-size picture."""
    from yt_dlp import YoutubeDL
    done, files, errors = [], [], []
    with YoutubeDL(_options(quality, folder, item, done)) as ydl:
        try:
            info = ydl.extract_info(item['url'], download=False)
        except Exception:
            if item['platform'] == 'tiktok' and _tiktok_photos(ydl, item, folder):
                return
            raise
        if info and info.get('title') and not item['title']:
            item['title'] = str(info['title'])[:140]
        entries = _entries(info)
        videos = [e for e in entries if e.get('url') or e.get('requested_formats')]
        pictures = [e for e in entries if e not in videos and e.get('thumbnails')] if quality != 'audio' else []
        for e in videos:
            try:
                before = len(done)
                ydl.process_info(dict(e))
                got = [p for p in dict.fromkeys(done[before:]) if os.path.isfile(p)]
                files += [p for p in got if p not in files]
            except Exception as err:
                errors.append(err)
        for k, e in enumerate(pictures, 1):
            try:
                stem = os.path.splitext(ydl.prepare_filename(e))[0] + (f' {k}' if len(pictures) > 1 else '')
                p = _save_picture(ydl, _best_picture(e), stem)
                if p:
                    files.append(p)
            except Exception as err:
                errors.append(err)
        files = [p for p in files if os.path.isfile(p)]
        if not files and item['platform'] == 'tiktok' and _tiktok_photos(ydl, item, folder):
            return
        item['files'] = files
        if not files and errors:
            raise errors[0]


def _best_picture(entry):
    thumbs = [t for t in entry.get('thumbnails') or [] if t.get('url')]
    if not thumbs:
        return None
    return max(thumbs, key=lambda t: ((t.get('width') or 0) * (t.get('height') or 0), t.get('preference') or 0))['url']


def _save_picture(ydl, url, stem):
    if not url:
        return None
    from yt_dlp.networking import Request
    with ydl.urlopen(Request(url, headers={'User-Agent': UA})) as r:
        data = r.read()
        ctype = (r.headers.get('Content-Type') or '').split(';')[0].strip().lower()
    if len(data) < 500:
        return None
    ext = IMAGE_EXT.get(ctype) or os.path.splitext(url.split('?')[0])[1][:5] or '.jpg'
    path = stem + ext
    with open(path, 'wb') as f:
        f.write(data)
    return path


def _tiktok_photos(ydl, item, folder):
    """TikTok photo posts (slideshows): the pictures from the post's page. -> True when it saved some."""
    from yt_dlp.networking import Request
    try:
        with ydl.urlopen(Request(item['url'], headers={'User-Agent': UA})) as r:
            html = r.read().decode('utf-8', 'replace')
        m = re.search(r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.+?)</script>', html, re.S)
        data = json.loads(m.group(1)) if m else {}
        post = (((data.get('__DEFAULT_SCOPE__') or {}).get('webapp.video-detail') or {}).get('itemInfo') or {}).get('itemStruct') or {}
        images = ((post.get('imagePost') or {}).get('images')) or []
        if not images:
            return False
        author = ((post.get('author') or {}).get('uniqueId') or 'tiktok')[:40]
        desc = re.sub(r'[\\/:*?"<>|\r\n\t]+', ' ', post.get('desc') or 'photo post')[:60].strip()
        files = []
        for k, im in enumerate(images, 1):
            urls = ((im.get('imageURL') or {}).get('urlList')) or []
            stem = os.path.join(folder, f'{author} - {desc} [{post.get("id", "")}] {k}')
            for u in urls:
                try:
                    p = _save_picture(ydl, u, stem)
                except Exception:
                    p = None
                if p:
                    files.append(p)
                    break
        item['files'] = files
        item['title'] = item['title'] or desc
        if files:
            item['error'] = ''
        return bool(files)
    except Exception as e:
        print('tiktok photos:', item['url'], e, flush=True)
        return False


def engine_version():
    try:
        from yt_dlp.version import __version__
        return __version__
    except Exception:
        return '?'
