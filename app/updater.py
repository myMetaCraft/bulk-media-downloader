"""Keeps the download engine fresh. Instagram, TikTok and YouTube change often and yt-dlp follows within days, so the app
fetches new yt-dlp releases itself (pure-Python wheels from PyPI, checked against PyPI's SHA-256) into its data folder.
A new engine is used from the next start. It also checks whether a newer version of the app itself is out.
"""
import os, re, sys, json, time, hashlib, zipfile, shutil, urllib.request

PACKAGES = {'yt-dlp': 'yt_dlp', 'yt-dlp-ejs': 'yt_dlp_ejs'}
APP_RELEASES = 'https://api.github.com/repos/myMetaCraft/bulk-media-downloader/releases/latest'
STATE = {'installed': [], 'app_latest': None, 'error': None, 'checked': None}


def _dir(home):
    return os.path.join(home, 'engine')


def _active_file(home):
    return os.path.join(_dir(home), 'active.json')


def activate(home):
    """Before yt_dlp is imported: put the newest fetched engine first on the path."""
    try:
        active = json.load(open(_active_file(home)))
    except (OSError, ValueError):
        return {}
    for pkg, info in active.items():
        path = info.get('path')
        if path and os.path.isdir(os.path.join(path, PACKAGES.get(pkg, '_'))) and path not in sys.path:
            sys.path.insert(0, path)
    return active


def _vtuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', v or '0'))


def _installed_version(pkg):
    mod = PACKAGES[pkg]
    try:
        if mod == 'yt_dlp':
            from yt_dlp.version import __version__
            return __version__
        from importlib.metadata import version
        return version(pkg)
    except Exception:
        return '0'


def _get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'BulkMediaDownloader', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _fetch_wheel(pkg, home):
    """-> new version installed, or None when the current one is the newest."""
    meta = _get_json(f'https://pypi.org/pypi/{pkg}/json')
    latest = meta['info']['version']
    if _vtuple(latest) <= _vtuple(_installed_version(pkg)):
        return None
    wheel = next((u for u in meta.get('urls', []) if u.get('packagetype') == 'bdist_wheel' and u['filename'].endswith('-py3-none-any.whl')), None)
    if not wheel:
        return None
    req = urllib.request.Request(wheel['url'], headers={'User-Agent': 'BulkMediaDownloader'})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if hashlib.sha256(data).hexdigest() != wheel['digests']['sha256']:
        raise RuntimeError(f'{pkg} {latest}: checksum does not match, not installed')
    target = os.path.join(_dir(home), f'{pkg}-{latest}')
    tmp = target + '.part'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    whl = os.path.join(tmp, wheel['filename'])
    with open(whl, 'wb') as f:
        f.write(data)
    with zipfile.ZipFile(whl) as z:
        for name in z.namelist():
            if name.startswith('/') or '..' in name.split('/'):
                raise RuntimeError('unsafe file in the wheel')
        z.extractall(tmp)
    os.remove(whl)
    shutil.rmtree(target, ignore_errors=True)
    os.replace(tmp, target)
    try:
        active = json.load(open(_active_file(home)))
    except (OSError, ValueError):
        active = {}
    old = (active.get(pkg) or {}).get('path')
    active[pkg] = {'version': latest, 'path': target, 'at': time.time()}
    with open(_active_file(home) + '.tmp', 'w') as f:
        json.dump(active, f)
    os.replace(_active_file(home) + '.tmp', _active_file(home))
    if old and old != target and os.path.isdir(old) and old not in sys.path:
        shutil.rmtree(old, ignore_errors=True)
    return latest


def check(home, app_version):
    """Background, once per start: newer engine and newer app?"""
    os.makedirs(_dir(home), exist_ok=True)
    for pkg in PACKAGES:
        try:
            v = _fetch_wheel(pkg, home)
            if v:
                STATE['installed'].append(f'{pkg} {v}')
                print('engine: installed', pkg, v, '(used from the next start)', flush=True)
        except Exception as e:
            STATE['error'] = f'{pkg}: {e}'
            print('engine update:', pkg, e, flush=True)
    try:
        tag = _get_json(APP_RELEASES).get('tag_name') or ''
        if tag and _vtuple(tag) > _vtuple(app_version):
            STATE['app_latest'] = tag.lstrip('v')
    except Exception as e:
        print('app update check:', e, flush=True)
    STATE['checked'] = time.time()
