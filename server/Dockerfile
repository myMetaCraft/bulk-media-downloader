FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL -o /tmp/deno.zip https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip \
 && unzip /tmp/deno.zip -d /usr/local/bin && rm /tmp/deno.zip && deno --version
RUN pip install --no-cache-dir "yt-dlp[default,curl-cffi]"
WORKDIR /app
COPY probe.py .
CMD ["python", "probe.py"]
