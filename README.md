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

- [Traefik Dashboard](http://traefik.here.ns0.co)
- [Portainer Dashboard](http://portainer.here.ns0.co)

## Configure your containers

To expose one of your services through Traefik, your service needs to be part of the `backplane` Docker network and carry a few Traefik-relevant labels:

### docker

```bash
docker run \
--network backplane \
--label "traefik.enable=true" \
--label "traefik.http.routers.whoami.rule=Host(\`whoami.here.ns0.co\`)" \
--label "traefik.http.routers.whoami.entrypoints=http" \
--rm traefik/whoami
```

Visit http://whoami.here.ns0.co to verify it worked.

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
      - "traefik.http.routers.whoami.rule=Host(`whoami.here.ns0.co`)"
      - "traefik.http.routers.whoami.entrypoints=http"
      - "traefik.docker.network=backplane"

networks:
  backplane:
    name: backplane
    external: true
```

Visit http://whoami.here.ns0.co to verify it worked.

## Use in production

**backplane** can be used on public cloud hosts, too:

```bash
backplane install --environment production --domain mydomain.com --mail letsencrypt@mydomain.com
backplane start
```

This enables the following additional features:

- access your backplane services through `mydomain.com` (NOTE: if you do not specify a domain, **backplane** will use a wildcard domain based on the IP of your server, like 127-0-0-1.nip.io)
- automatic SSL for your containers through LetsEncrypt
- configurable HTTP to HTTPS redirect
- sane security defaults

### docker

```bash
docker run \
--network backplane \
--label "traefik.enable=true" \
--label "traefik.http.routers.whoami.rule=Host(\`whoami.here.ns0.co\`)" \
--label "traefik.http.routers.whoami.entrypoints=http" \
--label "traefik.http.routers.whoami.middlewares=compress@docker" \
--label "traefik.http.routers.whoami.middlewares=https-redirect@docker" \
--label "traefik.http.routers.whoami-secure.entrypoints=https" \
--label "traefik.http.routers.whoami-secure.rule=Host(\`whoami.mydomain.com\`)" \
--label "traefik.http.routers.whoami-secure.tls=true" \
--label "traefik.http.routers.whoami-secure.tls.certresolver=letsencrypt" \
--label "traefik.http.routers.whoami-secure.middlewares=secured@docker" \
--label "traefik.http.routers.whoami-secure.middlewares=compress@docker" \
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