FROM python:3.9.13-alpine

# Copy files
WORKDIR /usr/src/pihole-cloudflare-dns-sync
COPY src/ ./
COPY config/ config/

# Create logs directory
RUN mkdir -p log

# Install the requirements
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1 \
  CLOUDFLARE_DOMAINS_TOKENS=domain1.com:token1,domain2.com:token2,domain3.com:token3 \
  PIHOLE_HOST=123.123.123.123 \
  PIHOLE_PORT=80 \
  USE_HTTPS=no \
  PIHOLE_PASSWORD=change_me \
  RUN_EVERY=5 

ENTRYPOINT python3 ./main.py
