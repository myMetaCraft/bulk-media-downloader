# Builds build\BulkMediaDownloader: Python (embeddable) with yt-dlp, the app, ffmpeg and deno.
# Runs on a GitHub Windows runner (.github/workflows/build.yml); needs Python 3.13 on PATH.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = (Resolve-Path "$PSScriptRoot\..").Path
$build = "$root\build"; $out = "$build\BulkMediaDownloader"; $dl = "$build\dl"
New-Item -ItemType Directory -Force $out, $dl, "$build\logs", "$out\bin" | Out-Null
$headers = @{ 'User-Agent' = 'bulk-media-downloader-build' }
if ($env:GH_TOKEN) { $headers['Authorization'] = "Bearer $env:GH_TOKEN" }

function Fetch($url, $file) {
  if (-not (Test-Path $file)) {
    Write-Host "download $url"
    & curl.exe -fsSL --retry 4 --retry-delay 5 -o $file $url
    if ($LASTEXITCODE -ne 0) { throw "download failed: $url" }
  }
}
function Asset($repo, $pattern) {
  $rel = Invoke-RestMethod -Headers $headers "https://api.github.com/repos/$repo/releases/latest"
  $a = $rel.assets | Where-Object { $_.name -match $pattern } | Sort-Object name -Descending | Select-Object -First 1
  if (-not $a) { throw "no asset like $pattern in $repo (has: $($rel.assets.name -join ', '))" }
  Write-Host "$repo $($rel.tag_name): $($a.name)"
  return $a.browser_download_url
}

# 1. Python, the same version as the runner's, as the small embeddable build, with yt-dlp and its helpers
$ver = (python -c "import platform; print(platform.python_version())").Trim()
Fetch "https://www.python.org/ftp/python/$ver/python-$ver-embed-amd64.zip" "$dl\python.zip"
Expand-Archive "$dl\python.zip" "$out\python" -Force
$zip = (Get-ChildItem "$out\python\python3*.zip" | Select-Object -First 1).Name
$pth = Get-ChildItem "$out\python\python3*._pth" | Select-Object -First 1
Set-Content -Encoding ascii $pth.FullName "$zip`r`n.`r`nLib\site-packages`r`n..\app`r`nimport site"
python -m pip install --disable-pip-version-check --no-warn-script-location --target "$out\python\Lib\site-packages" -r "$root\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }

# 2. the app
New-Item -ItemType Directory -Force "$out\app" | Out-Null
Copy-Item "$root\app\*.py", "$root\app\ui.html" "$out\app"
Copy-Item "$root\VERSION", "$root\NOTICE.txt" $out
Copy-Item "$PSScriptRoot\bmd.ico" "$out\bmd.ico"

# 3. ffmpeg (joins YouTube's separate picture and sound, makes MP3s)
$ff = Asset 'BtbN/FFmpeg-Builds' '^ffmpeg-n\d+\.\d+-latest-win64-gpl-\d+\.\d+\.zip$'
Fetch $ff "$dl\ffmpeg.zip"
Expand-Archive "$dl\ffmpeg.zip" "$dl\ffmpeg" -Force
Get-ChildItem -Recurse "$dl\ffmpeg" -Include ffmpeg.exe, ffprobe.exe | Copy-Item -Destination "$out\bin"
Get-ChildItem -Recurse "$dl\ffmpeg" -Include LICENSE.txt | Select-Object -First 1 | Copy-Item -Destination "$out\bin\FFMPEG-LICENSE.txt"

# 4. deno (yt-dlp needs a JavaScript runtime for YouTube)
$deno = Asset 'denoland/deno' '^deno-x86_64-pc-windows-msvc\.zip$'
Fetch $deno "$dl\deno.zip"
Expand-Archive "$dl\deno.zip" "$out\bin" -Force
& "$out\bin\deno.exe" --version
if ($LASTEXITCODE -ne 0) { throw 'deno does not run' }

& "$out\python\python.exe" -c "import yt_dlp, curl_cffi; from yt_dlp.version import __version__ as v; print('yt-dlp', v, 'curl_cffi', curl_cffi.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'yt-dlp does not import' }
Get-ChildItem $out | Format-Table Name | Out-String | Write-Host
