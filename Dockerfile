FROM python:3.9.13-alpine

# Copy files
WORKDIR /usr/src/app
COPY src/main.py requirements.txt ./

# Install the requirements
RUN pip install --no-cache-dir -r requirements.txt


ENV PYTHONUNBUFFERED=1 \
  CLOUDFLARE_API_TOKEN=change_me \
  CLOUDFLARE_DOMAIN=example.com \
  EXCLUDE_PROXIED_RECORDS=yes \
  PIHOLE_HOST=123.123.123.123 \
  PIHOLE_PORT=80 \
  USE_HTTPS=no \
  PIHOLE_PASSWORD=change_me \
  RUN_EVERY=5 

ENTRYPOINT python3 ./main.py