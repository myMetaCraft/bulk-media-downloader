"""Writes the website into site/ (run: python tools/make_site.py). Static pages, no tracking, no cookies."""
import os, json, html, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
DOMAIN = 'https://bulkmediadownloader.com'
DOWNLOAD = 'https://github.com/myMetaCraft/bulk-media-downloader/releases/latest/download/BulkMediaDownloader-Setup.exe'
VERSION = open(os.path.join(ROOT, 'VERSION')).read().strip()
TODAY = datetime.date.today().isoformat()
NAME = 'Bulk Media Downloader'

CSS = """
:root{--paper:#eef1f6;--card:#fff;--ink:#0e1b2e;--muted:#55657c;--line:#d5dce7;--cobalt:#2346d9;--cobalt-dark:#1a36ad;--marker:#f6d743}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.65 "Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif}
a{color:var(--cobalt);text-underline-offset:3px}
:focus-visible{outline:3px solid var(--cobalt);outline-offset:2px}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
.top{display:flex;align-items:center;gap:12px;padding:18px 0}
.top a.brand{display:flex;align-items:center;gap:10px;color:var(--ink);text-decoration:none;font-weight:650}
.top img{width:32px;height:32px;border-radius:8px}
.top nav{margin-left:auto;display:flex;gap:18px;font-size:15px;flex-wrap:wrap}
.top nav a{color:var(--muted);text-decoration:none}
.top nav a:hover{color:var(--ink)}
@media(max-width:700px){.top{flex-wrap:wrap}.top nav{margin-left:0;width:100%;overflow-x:auto;flex-wrap:nowrap;gap:16px;font-size:14px;white-space:nowrap;padding-bottom:4px}}
h1,h2,h3{font-family:"Segoe UI Variable Display","Segoe UI",system-ui,-apple-system,sans-serif;line-height:1.15;letter-spacing:-.015em}
h1{font-size:clamp(36px,6vw,64px);margin:24px 0 16px;font-weight:750;max-width:14em}
h1 .m{background:linear-gradient(transparent 60%,var(--marker) 60% 92%,transparent 92%)}
.sub h1{font-size:clamp(32px,5vw,50px)}
h2{font-size:clamp(26px,3.4vw,34px);margin:64px 0 14px;font-weight:700}
h3{font-size:19px;margin:0 0 6px;font-weight:650}
p.lead{font-size:20px;color:var(--muted);max-width:36em;margin:0 0 26px}
.cta{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.btn{display:inline-block;background:var(--cobalt);color:#fff;text-decoration:none;font-weight:650;padding:15px 26px;border-radius:12px;font-size:18px}
.btn:hover{background:var(--cobalt-dark)}
.small{font-size:14px;color:var(--muted)}
.hero{display:grid;grid-template-columns:1.05fr .95fr;gap:40px;align-items:center;padding:10px 0 20px}
@media(max-width:880px){.hero{grid-template-columns:1fr}}
.demo{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px;display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:center;font:13px/1.9 Consolas,"Cascadia Mono",ui-monospace,monospace}
.demo .col{background:#f6f8fb;border-radius:10px;padding:10px 12px;overflow:hidden}
.demo .col div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.demo .arrow{font:700 26px system-ui;color:var(--cobalt)}
.demo .files div::before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;background:var(--cobalt);margin-right:8px}
.demo .files div.ph::before{background:var(--marker)}
.cap{grid-column:1/-1;font:13px/1.4 system-ui;color:var(--muted);margin:2px 2px 0}
ol.steps{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(3,1fr);gap:16px;counter-reset:s}
@media(max-width:780px){ol.steps{grid-template-columns:1fr}}
ol.steps li{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;counter-increment:s}
ol.steps li::before{content:counter(s);display:inline-grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--ink);color:#fff;font-weight:700;margin-bottom:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
.card a.more{font-size:15px}
.why{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px 34px}
.why p{margin:4px 0 14px;color:var(--muted)}
.why h3{margin-top:8px}
details{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin-bottom:10px}
summary{cursor:pointer;font-weight:600}
details p{margin:10px 0 2px;color:var(--muted)}
.note{border-left:4px solid var(--marker);background:#fff;padding:14px 18px;border-radius:0 12px 12px 0;margin:28px 0}
.prose{max-width:46em}
.prose p,.prose li{color:#24344b}
.crumbs{font-size:14px;color:var(--muted);margin-top:10px}
.crumbs a{color:var(--muted)}
.end{background:var(--ink);color:#fff;border-radius:20px;padding:34px;margin:70px 0 30px;display:flex;gap:20px;align-items:center;flex-wrap:wrap}
.end h2{margin:0;color:#fff;font-size:28px}
.end .btn{background:var(--marker);color:var(--ink);margin-left:auto}
footer{border-top:1px solid var(--line);padding:24px 0 40px;font-size:14px;color:var(--muted)}
footer nav{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px}
footer a{color:var(--muted)}
"""

PAGES = {}


def page(slug, title, description, h1, body, faq=None, crumb=None):
    PAGES[slug] = dict(title=title, description=description, h1=h1, body=body, faq=faq or [], crumb=crumb)


def esc(s):
    return html.escape(s, quote=True)


NAV = [('/instagram-reels-downloader/', 'Instagram Reels'), ('/instagram-photo-downloader/', 'Instagram photos'),
       ('/tiktok-downloader/', 'TikTok'), ('/youtube-shorts-downloader/', 'YouTube Shorts'), ('/youtube-video-downloader/', 'YouTube videos')]


def cta(text='Download for Windows'):
    return (f'<div class="cta"><a class="btn" href="{DOWNLOAD}" id="download">{text}</a>'
            f'<span class="small">Free. Windows 10 and 11. No account, no ads.<br>Version {VERSION}</span></div>')


def faq_html(faq):
    if not faq:
        return ''
    items = ''.join(f'<details><summary>{esc(q)}</summary><p>{a}</p></details>' for q, a in faq)
    return f'<h2 id="faq">Questions</h2>{items}'


def render(slug, p):
    url = DOMAIN + slug
    ld = [{'@context': 'https://schema.org', '@type': 'SoftwareApplication', 'name': NAME, 'operatingSystem': 'Windows 10, Windows 11',
           'applicationCategory': 'MultimediaApplication', 'softwareVersion': VERSION, 'url': DOMAIN + '/', 'downloadUrl': DOWNLOAD,
           'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'},
           'description': 'Download videos and photos from many Instagram, TikTok and YouTube links at once.'}]
    if p['faq']:
        import re
        ld.append({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': re.sub('<[^>]+>', '', a)}} for q, a in p['faq']]})
    if p['crumb']:
        ld.append({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': NAME, 'item': DOMAIN + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': p['crumb'], 'item': url}]})
    nav = ''.join(f'<a href="{s}">{esc(t)}</a>' for s, t in NAV)
    crumbs = f'<div class="crumbs"><a href="/">{NAME}</a> / {esc(p["crumb"])}</div>' if p['crumb'] else ''
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(p['title'])}</title>
<meta name="description" content="{esc(p['description'])}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{esc(p['title'])}">
<meta property="og:description" content="{esc(p['description'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{DOMAIN}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#2346d9">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, separators=(',', ':'))}</script>
</head>
<body class="{'sub' if p['crumb'] else 'home'}">
<div class="wrap">
<header class="top"><a class="brand" href="/"><img src="/icon-512.png" alt="" width="32" height="32">{NAME}</a><nav aria-label="Downloaders">{nav}</nav></header>
{crumbs}
<main>
{p['body']}
{faq_html(p['faq'])}
<section class="end"><h2>Paste the links. Get the files.</h2><a class="btn" href="{DOWNLOAD}">Download for Windows</a></section>
</main>
<footer>
<nav><a href="/">Home</a>{nav}<a href="/privacy/">Privacy</a><a href="/terms/">Terms</a></nav>
<p>Download only what you created or have permission to use. {NAME} is not affiliated with Instagram, Meta, TikTok, YouTube or Google; their names are used only to say which links the app reads.</p>
</footer>
</div>
</body>
</html>
"""


# ------------------------------------------------------------------ home
page('/', 'Bulk Media Downloader: Free Bulk Video & Photo Downloader',
     'Paste up to 100 links and download Instagram Reels and photos, TikTok videos and YouTube Shorts and videos at once. Free Windows app, no account, no ads.',
     'Paste 30 links. Get 30 files.', f"""
<section class="hero">
  <div>
    <h1>Paste 30 links. <span class="m">Get 30 files.</span></h1>
    <p class="lead">{NAME} saves videos and photos from Instagram, TikTok and YouTube in one go. Paste the links, press Download, and every file lands in one folder, or one ZIP if you like.</p>
    {cta()}
  </div>
  <div class="demo" aria-label="Links in, files out">
    <div class="col"><div>instagram.com/reel/C9x…</div><div>tiktok.com/@chef/video/73…</div><div>youtube.com/shorts/Qk…</div><div>instagram.com/p/DAa…</div><div>youtu.be/dQw…</div><div>tiktok.com/@run/video/74…</div></div>
    <div class="arrow" aria-hidden="true">→</div>
    <div class="col files"><div>reel by chef.mp4</div><div>pasta in 60s.mp4</div><div>short by gym.mp4</div><div class="ph">carousel 1.jpg</div><div class="ph">carousel 2.jpg</div><div>full video.mp4</div></div>
    <p class="cap">Every batch gets its own folder in Downloads. Photos and carousels come out as pictures, videos as MP4.</p>
  </div>
</section>

<h2>How it works</h2>
<ol class="steps">
  <li><h3>Copy the links</h3>In Instagram, TikTok or YouTube, tap Share and Copy link. Collect as many as you want, in a note or a chat.</li>
  <li><h3>Paste them all at once</h3>Paste one link per line, or a whole message with links in it. The app finds every link and counts them.</li>
  <li><h3>Press Download</h3>Pick the quality, or audio only as MP3. The files download side by side and land in one folder.</li>
</ol>

<h2>What it downloads</h2>
<div class="grid">
  <div class="card"><h3>Instagram Reels</h3><p>Public reels and video posts in their original quality.</p><a class="more" href="/instagram-reels-downloader/">Instagram Reels downloader</a></div>
  <div class="card"><h3>Instagram photos</h3><p>Single photos and every slide of a carousel, in full size.</p><a class="more" href="/instagram-photo-downloader/">Instagram photo downloader</a></div>
  <div class="card"><h3>TikTok</h3><p>Public TikTok videos, many at once, saved as MP4.</p><a class="more" href="/tiktok-downloader/">TikTok downloader</a></div>
  <div class="card"><h3>YouTube Shorts</h3><p>Shorts as vertical MP4 files, or their sound as MP3.</p><a class="more" href="/youtube-shorts-downloader/">YouTube Shorts downloader</a></div>
  <div class="card"><h3>YouTube videos</h3><p>Long videos in up to 4K when the video has it, 1080p, 720p or MP3.</p><a class="more" href="/youtube-video-downloader/">YouTube video downloader</a></div>
</div>

<h2>Why an app, not a website</h2>
<div class="why">
  <div><h3>Many links, one click</h3><p>Websites take one link at a time. Here you paste up to 100 and walk away.</p></div>
  <div><h3>Your links stay on your computer</h3><p>The app downloads straight from your own internet connection. Your links are not sent to our servers, because there are none.</p></div>
  <div><h3>No ads, no pop-ups, no account</h3><p>Nothing to sign up for and nothing to click past. Open it, paste, download.</p></div>
  <div><h3>One folder, or one ZIP</h3><p>Each batch gets its own folder, named by date and time. Tick one box to also get everything in a single ZIP file.</p></div>
  <div><h3>Retry what failed</h3><p>A deleted or private post does not stop the rest. It is marked with the reason and a Retry button.</p></div>
  <div><h3>Keeps itself up to date</h3><p>Sites change often. The app fetches the newest version of its download engine by itself.</p></div>
</div>
<p class="note">Download only videos and photos you made yourself or have permission to use, and follow the rules of the site you download from. Private posts and posts that need a login cannot be downloaded.</p>
""", faq=[
    ('Is Bulk Media Downloader free?', 'Yes. The app is free, with no account, no ads and no limit on how often you use it. One batch can have up to 100 links.'),
    ('Which sites does it support?', 'Instagram (Reels, video posts, photos and carousels), TikTok videos, and YouTube Shorts and videos. Many other video sites work too, because the app is built on yt-dlp.'),
    ('Does it work on Mac or phones?', 'Not yet. It is a Windows app for Windows 10 and 11.'),
    ('Why does Windows show a blue warning when I install it?', 'Windows shows that warning for new apps that are not yet widely downloaded. Click More info, then Run anyway.'),
    ('Can I download private posts?', 'No. The app does not log in to your accounts, so it only downloads posts anyone can see without logging in.'),
    ('Where do the files go?', 'Into your Downloads folder, under Bulk Media Downloader, with one folder per batch. You can pick another folder in the app.'),
    ('Is it legal to download videos?', 'It depends on what you download and why. Downloading your own content, or content you have permission to use, is fine. Re-uploading other people\'s videos without permission is not. The sites\' own terms may also limit downloading. You are responsible for what you download.'),
])

# ------------------------------------------------------------------ platform pages
def platform_page(slug, crumb, title, desc, h1, lead, copy_steps, details_html, faq):
    body = f"""
<h1>{h1}</h1>
<p class="lead">{lead}</p>
{cta()}
<h2>How to download {crumb} in bulk</h2>
<ol class="steps">
  <li><h3>Copy the links</h3>{copy_steps}</li>
  <li><h3>Paste them in the app</h3>Open {NAME} and paste all the links at once. One per line, or a whole message: the app finds them.</li>
  <li><h3>Download</h3>Choose the quality and press Download. Every file lands in one folder, and in one ZIP if you tick that box.</li>
</ol>
<div class="prose">{details_html}</div>
<p class="note">Download only what you made or have permission to use. Posts that are private or need a login cannot be downloaded.</p>
"""
    page(slug, title, desc, h1, body, faq=faq, crumb=crumb)


platform_page('/instagram-reels-downloader/', 'Instagram Reels',
              'Instagram Reels Downloader: Download Many Reels at Once',
              'Download public Instagram Reels in bulk: paste 20, 30 or 100 reel links and get every video as MP4 in one folder or ZIP. Free Windows app.',
              'Instagram Reels downloader for <span class="m">many reels at once</span>',
              'Save public Instagram Reels by the dozen. Paste the reel links, press Download, and get every reel as an MP4 file in its original quality.',
              'In Instagram, open a reel, tap the paper plane or the three dots, then Copy link. Do it for every reel you want.',
              """<h2>What you get</h2>
<p>Each reel is saved as an MP4 file named after the account and the caption, so you can tell them apart at a glance. Reels download one after another with a short pause between them, because Instagram limits how fast visitors who are not logged in can open posts. A batch of 30 reels usually takes a few minutes.</p>
<p>Links to normal posts work too: a video post is saved as a video, a photo post as pictures, and a carousel slide by slide. For photo posts, see the <a href="/instagram-photo-downloader/">Instagram photo downloader</a>.</p>
<h2>Good to know</h2>
<ul><li>Only public reels can be downloaded. The app never asks for your Instagram login.</li>
<li>If Instagram shows a reel only to logged-in users, the app marks it with the reason, and the rest of the batch goes on.</li>
<li>If Instagram starts limiting downloads, wait a few minutes and press Retry on the reels that failed.</li></ul>""",
              [('How many reels can I download at once?', 'Up to 100 links in one batch. Start another batch whenever you want.'),
               ('Are the reels saved in full quality?', 'Yes, the app saves the best version Instagram offers, as MP4.'),
               ('Do I need an Instagram account?', 'No. The app only downloads public reels, without logging in.'),
               ('Can I save only the sound of a reel?', 'Yes. Choose Audio only (MP3) as the quality.')])

platform_page('/instagram-photo-downloader/', 'Instagram photos',
              'Instagram Photo Downloader: Save Posts and Carousels in Bulk',
              'Download public Instagram photos and every slide of a carousel in full size. Paste many post links at once and get the pictures in one folder. Free for Windows.',
              'Instagram photo downloader, <span class="m">carousels included</span>',
              'Save the photos of public Instagram posts in full size: single pictures and every slide of a carousel, from many posts at once.',
              'In Instagram, open a post, tap the paper plane or the three dots, then Copy link.',
              """<h2>What you get</h2>
<p>Every photo is saved in the largest size Instagram offers. A carousel with several slides gives you one file per slide, numbered in order, and video slides inside a carousel are saved as MP4 next to the pictures.</p>
<h2>Good to know</h2>
<ul><li>Only public posts can be downloaded; the app never logs in to Instagram.</li>
<li>Choosing Audio only (MP3) skips photos, so keep a video quality selected for photo posts.</li>
<li>For reels, see the <a href="/instagram-reels-downloader/">Instagram Reels downloader</a>.</li></ul>""",
              [('Does it download every slide of a carousel?', 'Yes. Each slide is saved as its own file, numbered in order.'),
               ('In what size are the photos saved?', 'In the largest size Instagram makes available for the post.'),
               ('Can I download photos from a private account?', 'No. Only posts anyone can see without logging in.')])

platform_page('/tiktok-downloader/', 'TikTok',
              'TikTok Downloader: Bulk Download TikTok Videos for Free',
              'Download many public TikTok videos at once. Paste the links, press Download and get every TikTok as MP4 in one folder or ZIP. Free Windows app, no account.',
              'TikTok downloader for <span class="m">many videos at once</span>',
              'Paste a list of TikTok links and get every video as an MP4 file. No account and no ads, and no pasting links one by one into a website.',
              'In TikTok, tap Share on a video, then Copy link. Short links like vm.tiktok.com work too.',
              """<h2>What you get</h2>
<p>Each TikTok is saved as an MP4 file named after the creator and the caption. Several videos download side by side, so a list of 30 is done quickly. Choose Audio only (MP3) if you only need the sound.</p>
<p>Photo posts (slideshows) are saved as pictures when TikTok shows them without a login.</p>
<h2>Good to know</h2>
<ul><li>Only public videos can be downloaded; the app never logs in to TikTok.</li>
<li>A video that was deleted or made private is marked with the reason, and the rest of the batch goes on.</li></ul>""",
              [('Can I paste short TikTok links?', 'Yes. Links like vm.tiktok.com/… and full links both work.'),
               ('How many TikTok videos can I download at once?', 'Up to 100 links per batch.'),
               ('Can I download just the sound?', 'Yes. Choose Audio only (MP3) as the quality.')])

platform_page('/youtube-shorts-downloader/', 'YouTube Shorts',
              'YouTube Shorts Downloader: Download Shorts in Bulk',
              'Download many YouTube Shorts at once as vertical MP4 files, or their sound as MP3. Paste the links and press Download. Free Windows app, no account, no ads.',
              'YouTube Shorts downloader for <span class="m">whole lists of Shorts</span>',
              'Collect the Shorts you need, paste all their links, and get every Short as a vertical MP4 file in one folder.',
              'In YouTube, tap Share on a Short, then Copy link. Links like youtube.com/shorts/… work.',
              """<h2>What you get</h2>
<p>Each Short is saved as an MP4 file in the best quality YouTube offers, or capped at 1080p or 720p if you want smaller files. Audio only (MP3) saves just the sound.</p>
<p>For long videos, see the <a href="/youtube-video-downloader/">YouTube video downloader</a>.</p>
<h2>Good to know</h2>
<ul><li>Age-restricted Shorts need a login and cannot be downloaded.</li>
<li>If YouTube asks to confirm you are not a bot, wait a while and press Retry.</li></ul>""",
              [('Are Shorts saved vertically?', 'Yes, in the same 9:16 shape as on YouTube.'),
               ('Can I download Shorts as MP3?', 'Yes. Choose Audio only (MP3) as the quality.'),
               ('How many Shorts at once?', 'Up to 100 links per batch.')])

platform_page('/youtube-video-downloader/', 'YouTube videos',
              'YouTube Video Downloader: Bulk Download in HD or MP3',
              'Download many YouTube videos at once in up to 4K, 1080p or 720p, or as MP3. Paste the links and get every video in one folder. Free Windows app, no ads.',
              'YouTube video downloader: <span class="m">many videos, one click</span>',
              'Paste a list of YouTube links and download every video in the quality you choose: the best available (up to 4K), 1080p, 720p, or audio only as MP3.',
              'In YouTube, tap Share under a video, then Copy link. Links like youtu.be/… and youtube.com/watch?v=… both work.',
              """<h2>What you get</h2>
<p>YouTube keeps the picture and the sound of high-quality videos apart; the app joins them into one MP4 file for you. "Up to 1080p" and "Up to 720p" prefer the most compatible format, which plays everywhere and opens in every video editor.</p>
<p>A link to a video inside a playlist downloads only that video.</p>
<h2>Good to know</h2>
<ul><li>Age-restricted and members-only videos need a login and cannot be downloaded.</li>
<li>Long videos in 4K are large; check you have enough free space.</li>
<li>For Shorts, see the <a href="/youtube-shorts-downloader/">YouTube Shorts downloader</a>.</li></ul>""",
              [('Can I download YouTube videos in 4K?', 'Yes, when the video is available in 4K, choose Best quality.'),
               ('Can I download YouTube as MP3?', 'Yes. Choose Audio only (MP3).'),
               ('Does a playlist link download the whole playlist?', 'A link to one video in a playlist downloads that video only.')])

# ------------------------------------------------------------------ legal
page('/privacy/', 'Privacy | Bulk Media Downloader', 'Bulk Media Downloader collects no personal data: no account, no tracking, no analytics.',
     'Privacy', f"""<h1>Privacy</h1><div class="prose">
<p>Updated {TODAY}.</p>
<h2>The app</h2>
<p>{NAME} runs on your computer. The links you paste and the files you download stay on your computer: the app downloads straight from the sites you link to, using your own internet connection. We do not run servers that receive your links or files.</p>
<p>The app connects to the internet only to download the links you give it, to check for a newer version of its download engine (from PyPI, the Python package index), and to check whether a newer version of the app is out (from GitHub). These requests carry no information about you or your downloads.</p>
<p>Settings and a small log file are kept in your user folder (%LOCALAPPDATA%\\Bulk Media Downloader). Uninstalling the app removes the program; you can delete that folder too.</p>
<h2>This website</h2>
<p>This website uses no cookies, no analytics and no ads. It is hosted on GitHub Pages; GitHub may log technical data such as IP addresses to run and protect its service. The download is served by GitHub.</p>
</div>""", crumb='Privacy')

page('/terms/', 'Terms | Bulk Media Downloader', 'The terms of use of Bulk Media Downloader, a free Windows app.',
     'Terms', f"""<h1>Terms of use</h1><div class="prose">
<p>Updated {TODAY}.</p>
<p>{NAME} is free software, provided as it is, without any warranty. We are not liable for any damage from using it, as far as the law allows.</p>
<p>You may download only content you created or have the right to use, and you must follow the terms of the sites you download from. You are responsible for what you download and what you do with it. Do not use the app to infringe anyone's copyright or other rights.</p>
<p>{NAME} is not affiliated with, endorsed by or sponsored by Instagram, Meta, TikTok, ByteDance, YouTube or Google. Their names are trademarks of their owners and are used only to say which links the app can read.</p>
<p>The app includes open-source components (yt-dlp, FFmpeg, Deno, Python and others) under their own licenses; see NOTICE.txt in the app's folder.</p>
</div>""", crumb='Terms')


def write():
    for slug, p in PAGES.items():
        folder = os.path.join(SITE, slug.strip('/'))
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(render(slug, p))
    urls = ''.join(f'<url><loc>{DOMAIN}{s}</loc><lastmod>{TODAY}</lastmod></url>' for s in PAGES)
    with open(os.path.join(SITE, 'sitemap.xml'), 'w') as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    with open(os.path.join(SITE, 'robots.txt'), 'w') as f:
        f.write(f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n')
    with open(os.path.join(SITE, 'CNAME'), 'w') as f:
        f.write('bulkmediadownloader.com\n')
    with open(os.path.join(SITE, '404.html'), 'w', encoding='utf-8') as f:
        f.write(render('/404.html', dict(title='Page not found | Bulk Media Downloader', description='This page does not exist.', h1='',
                                         body='<h1>This page does not exist.</h1><p class="lead">Go to the <a href="/">home page</a> to download the app.</p>',
                                         faq=[], crumb=None)).replace('<meta name="robots" content="index, follow, max-image-preview:large">',
                                                                      '<meta name="robots" content="noindex">'))
    print('wrote', len(PAGES), 'pages')


if __name__ == '__main__':
    write()
