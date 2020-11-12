# backplane

A dead-simple backplane for your Docker containers.

- [Traefik](https://doc.traefik.io/traefik/getting-started/quick-start/) reverse-proxy for your containers
- [Portainer](https://www.portainer.io/) management dashboard for Docker

## Get started

```bash
pip install backplane
backplane install
backplane start
```

You can now visit the dashboards of both services in your browser:

- [Traefik Dashboard](http://traefik.127-0-0-1.nip.io)
- [Portainer Dashboard](http://portainer.127-0-0-1.nip.io)

## Configure your containers

To expose one of your services through Traefik, hook it up to the `backplane` Docker network and add a label called `backplane.enabled` with value `true`. Traefik will pick up the container's `name` and expose it as a subdomain of your **BACKPLANE_DOMAIN** (defaults to `127-0-0-1.nip.io`):

### docker

```bash
docker run \
--network backplane \
--name whoami \
--label "backplane.enabled=true" \
--rm traefik/whoami
```

Your container will be exposed as [http://whoami.127-0-0-1.nip.io](http://whoami.127-0-0-1.nip.io).

### docker-compose

```bash
version: "3.3"

services:
  whoami:
    image: "traefik/whoami"
    container_name: "whoami"
    networks:
      - backplane
    labels:
      - "backplane.enabled=true"

networks:
  backplane:
    name: backplane
    external: true
```

Your container will be exposed as [http://whoami.127-0-0-1.nip.io](http://whoami.127-0-0-1.nip.io).

## Use in production

**backplane** can be used on public cloud hosts, too. Simply change `--environment` to `production` and add a mail address for LetsEncrypt. An optional `--domain` can be set on installation (defaults to `$SERVER_IP.nip.io`, e.g. `193-43-54-23.nip.io`).

```bash
backplane install --environment production --mail letsencrypt@mydomain.com [--domain mydomain.com]
backplane start
```

This enables the following additional features:

- access your backplane services through `mydomain.com`
- automatic SSL for your containers through LetsEncrypt (HTTP-Validation)
- automatic HTTP to HTTPS redirect
- sane security defaults

### docker

```bash
docker run \
--network backplane \
--name whoami \
--label "backplane.enabled=true" \
--rm traefik/whoami
```

### docker-compose

```bash
version: "3.3"

services:
  whoami:
    image: "traefik/whoami"
    container_name: "simple-service"
    networks:
      - backplane
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.whoami.entrypoints=http"
      - "traefik.http.routers.whoami.rule=Host(`whoami.mydomain.com`)"
      - "traefik.http.routers.whoami.middlewares=compress@docker"
      - "traefik.http.routers.whoami.middlewares=https-redirect@docker"
      - "traefik.http.routers.whoami-secure.entrypoints=https"
      - "traefik.http.routers.whoami-secure.rule=Host(`whoami.mydomain.com`)"
      - "traefik.http.routers.whoami-secure.tls=true"
      - "traefik.http.routers.whoami-secure.tls.certresolver=letsencrypt"
      - "traefik.http.routers.whoami-secure.middlewares=secured@docker"
      - "traefik.http.routers.whoami-secure.middlewares=compress@docker"
      - "traefik.docker.network=backplane"

networks:
  backplane:
    name: backplane
    external: true
```

## Use the Runner

### Update your ssh config

Add the following to `~/.ssh/config`. This allows you to reach the runner under `backplane` without further configuration.

```bash
Host backplane
    HostName 127.0.0.1
    User backplane
    Port 2222
```

### Update your git remote

Assuming your repository is called `myapp`, this is how you add the **backplane** runner to your git remotes:

```bash
git remote add origin "git@backplane:myapp"
```

## Configure your application

These are 

```bash
BACKPLANE_COMPOSE_FILE=docker-compose.yml
BACKPLANE_ENV_FILE=.env
```

## Development

### Dependencies

```bash
pip install poetry
poetry shell
poetry install
npm i -g standard-version
```

### Build

```bash
poetry build
```

### Publish

```bash
poetry publish
```