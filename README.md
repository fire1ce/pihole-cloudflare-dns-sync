# pihole-cloudflare-dns-sync

[![Build](https://github.com/fire1ce/pihole-cloudflare-dns-sync/actions/workflows/ci.yml/badge.svg)](https://github.com/fire1ce/pihole-cloudflare-dns-sync/actions/workflows/ci.yml) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) [![Docker Pulls](https://img.shields.io/docker/pulls/fire1ce/pihole-cloudflare-dns-sync.svg)](https://hub.docker.com/r/fire1ce/pihole-cloudflare-dns-sync) [![Docker Stars](https://img.shields.io/docker/stars/fire1ce/pihole-cloudflare-dns-sync.svg)](https://hub.docker.com/r/fire1ce/pihole-cloudflare-dns-sync) [![https://3os.org](https://img.shields.io/badge/Follow-https%3A%2F%2F3os.org-orange)](https://3os.org) [![Contribution is Welcome](https://img.shields.io/badge/Contribution%20Is-Welcomed-brightgreen)](https://github.com/fire1ce/pihole-cloudflare-dns-sync)

## Description

Lightweight Container image based on [python:3.9.13-alpine][docker-hub-python-url] to be used in conjunction with a [Pi-hole][pi-hole-net-url] instance to sync the DNS records from [Cloudflare DNS Service][cloudflare-url] to **Pi-hole local DNS**.

### Supports

- A records
- CNAME records
- Any type of Pi-hole instance

## Requirements

- Cloudflare API Readonly Token
- Pi-hole instance

### Creating a Cloudflare API token

To create a CloudFlare API token for your DNS zone go to [https://dash.cloudflare.com/profile/api-tokens][cloudflare-api-token-url] and follow these steps:

1. Click Create Token
2. Select Create Custom Token
3. Provide the token a name, for example, `example.com-dns-zone-readonly`
4. Grant the token the following permissions:
   - Zone - DNS - Read
5. Set the zone resources to:
   - Include - Specific Zone - `example.com`
6. Complete the wizard and use the generated token at the `CLOUDFLARE_API_TOKEN` variable for the container

## Parameters

| Parameter               | Description             | Default         | Type    | Required |
| ----------------------- | ----------------------- | --------------- | ------- | -------- |
| CLOUDFLARE_API_TOKEN    | Cloudflare API Token    | change_me       | string  | Yes      |
| CLOUDFLARE_DOMAIN       | Cloudflare Domain       | example.com     | string  | Yes      |
| EXCLUDE_PROXIED_RECORDS | Exclude Proxied Records | yes             | string  | Yes      |
| PIHOLE_HOST             | Pi-hole hostname/IP     | 123.123.123.123 | string  | Yes      |
| PIHOLE_PORT             | Pi-hole port            | 80              | integer | Yes      |
| USE_HTTPS               | http/https for pihole   | no              | string  | Yes      |
| PIHOLE_PASSWORD         | Pi-hole password        | change_me       | string  | Yes      |
| RUN_EVERY               | Run very x minute       | 5               | integer | Yes      |

## Usage

Docker run example:

```shell
docker run -d \
  --name pihole-cloudflare-dns-sync \
  -h pihole-cloudflare-dns-sync \
  --restart always \
  -v /etc/timezone:/etc/timezone:ro \
  -v /etc/localtime:/etc/localtime:ro \
  -e CLOUDFLARE_API_TOKEN=cloudflare_secret_dns_zone_api_token \
  -e CLOUDFLARE_DOMAIN=example.com \
  -e EXCLUDE_PROXIED_RECORDS=yes \
  -e PIHOLE_HOST=123.123.123.123 \
  -e PIHOLE_PORT=80 \
  -e USE_HTTPS=no \
  -e PIHOLE_PASSWORD=secret \
  -e RUN_EVERY=1 \
  -e PUID=1000 \
  -e PGID=1000 \
fire1ce/pihole-cloudflare-dns-sync
```

Docker compose example:

```yml
version: '3'

services:
  pihole-cloudflare-dns-sync:
    image: fire1ce/pihole-cloudflare-dns-sync
    container_name: pihole-cloudflare-dns-sync
    hostname: pihole-cloudflare-dns-sync
    restart: always
    network_mode: bridge
    volumes:
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    environment:
      - CLOUDFLARE_API_TOKEN=cloudflare_secret_dns_zone_api_token
      - CLOUDFLARE_DOMAIN=example.com
      - EXCLUDE_PROXIED_RECORDS=yes
      - PIHOLE_HOST=123.123.123.123
      - PIHOLE_PORT=80
      - USE_HTTPS=no
      - PIHOLE_PASSWORD=secret
      - RUN_EVERY=1
      - PUID=1000
      - PGID=1000
```

## License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE][license-url] file for details

<!-- appendices -->

<!-- urls -->

[pi-hole-net-url]: https://pi-hole.net/ 'Pi-hole Website'
[cloudflare-url]: https://www.cloudflare.com/ 'Cloudflare Website'
[cloudflare-api-token-url]: https://dash.cloudflare.com/profile/api-tokens 'Cloudflare API Token'
[docker-hub-python-url]: https://hub.docker.com/_/python?tab=tags 'Docker Hub Python'
[license-url]: https://github.com/fire1ce/pihole-cloudflare-dns-sync/blob/main/LICENSE.md 'LICENSE'

<!-- end appendices -->
