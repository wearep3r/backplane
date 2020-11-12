<div>
  <img align="left" src="logo.png" width="175" alt="logo" />
  <h1 align="left">backplane</h1>
</div>

**[Website](https://backplane.sh)** — **[Documentation](https://backplane.sh/docs)**

A dead-simple backplane for your Docker Compose services. No more friction between development and production environments. `git push` to deploy.

[!["Version"](https://img.shields.io/github/v/tag/wearep3r/backplane?label=version)](https://github.com/wearep3r/backplane)
[!["p3r. Slack"](https://img.shields.io/badge/slack-@wearep3r/general-purple.svg?logo=slack&label=Slack)](https://join.slack.com/t/wearep3r/shared_invite/zt-d9ao21f9-pb70o46~82P~gxDTNy_JWw)

---

## Get started

```bash
pip install backplane
backplane install
backplane start
```

You can now visit the dashboards of Traefik and Portainer in your browser:

- [Traefik Dashboard](http://traefik.127-0-0-1.nip.io)
- [Portainer Dashboard](http://portainer.127-0-0-1.nip.io)

## Configure your containers

To expose one of your services through **backplane**, hook it up to the `backplane` Docker network and add a label called `backplane.enabled` with value `true`. **backplane** will pick up the container's `name` and expose it as a subdomain of your **BACKPLANE_DOMAIN** (defaults to `127-0-0-1.nip.io`):

### docker-compose

```yaml
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

- access your backplane services as subdomains of `mydomain.com`
- automatic SSL for your containers through LetsEncrypt (HTTP-Validation)
- automatic HTTP to HTTPS redirect
- sane security defaults

### docker-compose

```yaml
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

## Deploy to backplane

`git push` your code to the built-in **runner** for dead-simple auto-deployment of your Docker Compose Service. The runner deploys whatever you define in the repository's `docker-compose.yml` file and can load additional environment variables from a `.env` file.

### Update your ssh config

Add the following to your local `~/.ssh/config` file. This allows you to reach the runner under `backplane` without further configuration.

```bash
Host backplane
    HostName 127.0.0.1
    User backplane
    Port 2222
```

> **NOTE**: replace "HostName" with your server's IP if you're running in production

### Update your git remote

Assuming your repository is called `whoami`, this is how you add the **backplane runner** to your git remotes:

```bash
git remote add origin "git@backplane:whoami"
```

### Deploy to your server

```bash
git commit -am "feat: figured out who I am"
git push backplane master
```

That's it!

## What is backplane

**backplane** consists of 3 main services:

- [Traefik](#), a very popular, cloud-native reverse-proxy
- [Portainer](#), a very popular management interface for Docker
- [backplane Runner](#), a simple CI/CD server

It aims to provide simple access to core prerequisites of modern app development:

- Endpoint exposure
- Container management
- Deployment workflows

To develop and run modern web-based applications you need a few core ingredients, like a reverse-proxy handling request routing, a way to manage containers and a way to deploy your code. **backplane** offers this for local development as well as on production nodes in a seemless way.

The runner makes it easy to bypass long CI pipelines and deploy your application to a remote backplane host with ease. 

**backplane** is mainly aimed at small to medium sized development teams or solo-developers that don't require complex infrastructure. Use it for rapid prototyping or simple deployment scenarios where the full weight of modern CI/CD offerings just isn't bearable.

You can migrate from local development to production with a simple `git push` when using **backplane** on both ends. Think of it as a micro-PaaS that you can use locally.

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