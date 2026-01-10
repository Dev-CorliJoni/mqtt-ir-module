FROM node:20-alpine AS frontend
WORKDIR /app

COPY frontend/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend/ ./
RUN npm run build


FROM debian:bookworm-slim AS backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    v4l-utils \
    python3 python3-venv \
    tini \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY backend/requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir -r /opt/app/requirements.txt

COPY backend /opt/app
COPY --from=frontend /app/dist /opt/app/static

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DATA_DIR=/data
ENV IR_RX_DEVICE=/dev/lirc0
ENV DEBUG=false

EXPOSE 80

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/entrypoint.sh"]
