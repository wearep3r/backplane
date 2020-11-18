<div>
  <img align="left" src="https://raw.githubusercontent.com/wearep3r/backplane/master/logo.png" width="175" alt="logo" />
  <h1 align="left">backplane</h1>
</div>

**[Website](https://backplane.sh)** — **[Documentation](https://backplane.sh/docs)** — **[Source Code](https://github.com/wearep3r/backplane)**

A dead-simple backplane for your Docker Compose services with free SSL and Git-based continuous delivery. No more friction between development and production environments.

[!["Version"](https://img.shields.io/github/v/tag/wearep3r/backplane?label=version)](https://github.com/wearep3r/backplane)
[!["p3r. Slack"](https://img.shields.io/badge/slack-@wearep3r/general-purple.svg?logo=slack&label=Slack)](https://join.slack.com/t/wearep3r/shared_invite/zt-d9ao21f9-pb70o46~82P~gxDTNy_JWw)

---

## Get started

> 🚀 Check out our [Examples](examples) section for quick-start templates for [Wordpress](examples/wordpress), [Sonarqube](examples/sonarqube) and more

```bash
pip install backplane
backplane init
backplane up
```

You can now visit the dashboards of Traefik and Portainer in your browser:

- [Traefik Dashboard](http://traefik.127-0-0-1.nip.io)
- [Portainer Dashboard](http://portainer.127-0-0-1.nip.io)

## Configure your containers

Exposing one of your services through **backplane** is easy:

- add it to the `backplane` Docker network 
- add a label `backplane.enabled` with value `true`

**backplane** will automatically pick up the services's name (e.g. `whoami`) and exposes it as a subdomain of your **backplane domain** (defaults to `127-0-0-1.nip.io`).

> **NOTE**: this assumes that your service is accessible on port 80 inside the container. If that is NOT the case, see [Advanced configuration](#-advanced-configuration)

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

Your container will be exposed as [https://whoami.mydomain.com](https://whoami.mydomain.com).

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

That's it! **backplane** will build and deploy your application and expose it automatically.

## What is backplane

**backplane** consists of 3 main services:

- [Traefik](#), a very popular, cloud-native reverse-proxy
- [Portainer](#), a very popular management interface for Docker
- [backplane Runner](#), a simple Continuous Delivery server

It aims to provide simple access to core prerequisites of modern app development:

- Endpoint exposure
- Container management
- Deployment workflows

To develop and run modern web-based applications you need a few core ingredients, like a reverse-proxy handling request routing, a way to manage containers and a way to deploy your code. **backplane** offers this for local development as well as on production nodes in a seemless way.

The runner makes it easy to bypass long CI pipelines and deploy your application to a remote backplane host with ease. 

**backplane** is mainly aimed at small to medium sized development teams or solo-developers that don't require complex infrastructure. Use it for rapid prototyping or simple deployment scenarios where the full weight of modern CI/CD offerings just isn't bearable.

You can migrate from local development to production with a simple `git push` when using **backplane** on both ends. Think of it as a micro-PaaS that you can use locally.

## Advanced configuration

**backplane** is only a thin wrapper around Traefik. If you require more complex routing scenarios or have more complex service setups (e.g. multiple domains per container), simply use Traefik's label-based configuration.

[Read more](https://doc.traefik.io/traefik/) in the docs.

### Expose containers with non-standard ports

**backplane** expects your services to listen to port 80 inside their containers. If that is not the case, you need to tell the backplane about it. Add the following additional labels to tell backplane your service is accessible on port 9000:

```yaml
labels:
  - backplane.enabled=true
  - "traefik.http.routers.custom.service=custom-http"
  - "traefik.http.services.custom-http.loadbalancer.server.port=9000"
```

## Examples

In the [examples](examples) directory you'll find examples showing how to integrate backplane with your existing services

Change to any of the example folders and run `docker-compose up`. The example's `README` will hold additional information on how to use it.

## Development

### Dependencies

```bash
pip install poetry
poetry shell
poetry install
```

### Build

```bash
poetry build
```

### Generate release

```bash
semantic-release version
```

### Publish release

```bash
semantic-release publish
```