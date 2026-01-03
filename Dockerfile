# Dockerfile
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    lirc \
    python3 python3-venv \
    tini \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY app/requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir -r /opt/app/requirements.txt

COPY lirc_options.conf /etc/lirc/lirc_options.conf

COPY app /opt/app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DATA_DIR=/data
ENV IR_DEVICE=/dev/lirc0

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/entrypoint.sh"]