FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC and websockify
RUN git clone --branch v1.5.0 https://github.com/novnc/noVNC.git /usr/share/novnc && \
    git clone --branch v0.12.0 https://github.com/novnc/websockify /usr/share/novnc/utils/websockify && \
    rm -rf /usr/share/novnc/.git /usr/share/novnc/utils/websockify/.git && \
    ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html

# Install Python dependencies for the proxy
RUN pip install --no-cache-dir \
    websockify \
    aiohttp \
    pyyaml

# Copy configuration files
COPY image/nginx.conf /etc/nginx/nginx.conf
COPY image/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY image/proxy.py /app/proxy.py
COPY image/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Create necessary directories
RUN mkdir -p /var/log/supervisor /var/run

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]