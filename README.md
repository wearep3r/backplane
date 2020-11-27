<div>
  <img align="left" src="https://raw.githubusercontent.com/wearep3r/backplane/master/logo.png" width="175" alt="logo" />
  <h1 align="left">backplane</h1>
</div>

**[Website](https://backplane.sh)** — **[Documentation](https://backplane.sh/docs)** — **[Source Code](https://github.com/wearep3r/backplane)**

A dead-simple backplane for your Docker Compose services - with free SSL and Git-based continuous delivery. Run any Docker app [manually](examples/) or from [backplane's app-store](http://portainer.127-0-0-1.ns0.co/#!/1/docker/templates) in no time.

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

You can now visit the dashboards of [Traefik](https://doc.traefik.io/traefik/) and [Portainer](https://www.portainer.io/) in your browser:

- [traefik.127-0-0-1.ns0.co](http://traefik.127-0-0-1.ns0.co)
- [portainer.127-0-0-1.ns0.co](http://portainer.127-0-0-1.ns0.co)

## Configure your Docker Compose services

Exposing one of your services through **backplane** is easy:

- add it to the `backplane` Docker network 
- add a label `backplane.enabled` with value `true`

**backplane** will automatically pick up the service's name (e.g. `whoami`) and exposes it as a subdomain of your **backplane domain** (defaults to `127-0-0-1.ns0.co`).

> **NOTE**: this assumes that your service is accessible on port 80 inside the container. If that is NOT the case, see [Advanced configuration](#-advanced-configuration)

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
    external: true
```

Your service will be exposed as [http://whoami.127-0-0-1.ns0.co](http://whoami.127-0-0-1.ns0.co).

## Use backplane with HTTPS

Use `--https` and add a mail address for LetsEncrypt on installation to enable additional security for your applications. An optional `--domain` can be set on installation (defaults to `$SERVER_IP.ns0.co`, e.g. `193-43-54-23.ns0.co` if `--https` is set).

```bash
backplane init --https --mail letsencrypt@mydomain.com [--domain mydomain.com]
backplane up
```

This enables the following additional features:

- access your Docker Compose services as subdomains of `mydomain.com`
- automatic SSL for your Docker Compose services through LetsEncrypt (HTTP-Validation, so this doesn't work on your developer machine unless you deal with the necessary port-forwardings)
- automatic HTTP to HTTPS redirect
- sane security defaults

The Docker Compose stack definition doesn't change from the one without `--https`. **backplane** deals with the necessary configuration.

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
    external: true
```

Your container will be exposed as [https://whoami.mydomain.com](https://whoami.mydomain.com).

## Authentication

The default username for authentication with backplane services is `admin`, the default password is `backplane`.

Assuming you don't want to roll with the defaults when running **backplane** on a public server, you can add `--user` and `--password` to the `init` command to specify your own values.

```bash
backplane init --https --user testuser --password testpassword
```

### Authentication for your services

Traefik comes with a [BasicAuth Middleware](https://doc.traefik.io/traefik/middlewares/basicauth/) that you can use to protect your services with the username and password configured above. All you need to do is to activate the Traefik middleware for your service:

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
      - "traefik.http.routers.whoami.middlewares=auth@docker"

networks:
  backplane:
    external: true
```

When initalized with `--https`, authentication will be activated for Traefik and Portainer automatically.

## Deploy to backplane (Experimental)

> **NOTE**: this is still WIP and subject to change. We try to provide an unopinonated wrapper around docker-compose with a few "augmentations" that is fully compatible with **standard** Docker Compose stacks. We also plan to integrate with Portainer's templating system to make installing applications even easier.

**backplane** offers multiple ways to launch your applications. They all expect your application to live inside a repository (i.e. a directory). **backplane** can deploy from a plain directory or local and remote git repositories.

**backplane** implements a simple workflow around `docker-compose` to "install" your applications to a Docker engine it has access to. Basically **backplane** does this:

- load variables from `.env`
- augment with global configuration (i.e. `BACKPLANE_DOMAIN=127-0-0-1.ns0.co`)
- use `--build` if necessary (i.e. if there's a `build:` section in `docker-compose.yml`)
- run `docker-compose up -d`

**backplane** (as of now) does not take care of the lifecycle of the application. To interface with it, use the bundled Portainer to manage your application from a UI or fall back to standard docker/docker-compose tooling.

Installed applications will be saved to your local **backplane** config (default: `~/.backplane/contexts/default/backplane.yml`).

An application that can be installed with **backplane** should contain:

- a `docker-compose.yml` file
- an optional `.env` file configuring your stack
- the application code
- an optional `Dockerfile` to build the application (**backplane** expects the `build:` section of the `docker-compose.yml` file to be correctly configured)

Here are a few examples:

- [Grafana Loki](https://github.com/backplane-apps/loki)
- [Docker Registry](https://github.com/backplane-apps/registry)
- [backplane itself](https://github.com/wearep3r/backplane)

### With the CLI

**backplane** can deploy an application directly from its repository directory. Assuming your application provides the necessary files, just run the following command from within your application directory:

```bash
backplane install
```

Optional arguments:

- `name`: the name of your application (translates to the `docker-compose` project, i.e. `-p NAME`); defaults to the name of the application directory (i.e. `$PWD`)
- `path`: the path of your application; defaults to the current directory (i.e. `$PWD`)
- `--from` (or `-f`): a git repository (directory or URL) where **backplane** can find the application; if specified, **backplane** ignores the `path` argument and tries to install the application by cloning the repository from the given source to `~/.backplane/contexts/default/apps/$NAME`, where `$NAME` equals to the `NAME` argument (if given) or defaults to the name of the git repository

#### Examples

**local directory, custom name**:

```bash
backplane install my-awesome-app-beta $HOME/development/my-awesome-app
```

- sets the application name to `my-awesome-app-beta`
- installs the application from `$HOME/development/my-awesome-app`

**remote git repository, default name**:

```bash
backplane install --from https://github.com/backplane-apps/registry
```

- clones `https://github.com/backplane-apps/registry` to `~/.backplane/contexts/default/apps/registry`
- installs the application from `~/.backplane/contexts/default/apps/registry`

**local git repository, default name**:

```bash
backplane install --from $HOME/development/my-awesome-app
```

- clones `$HOME/development/my-awesome-app` to `~/.backplane/contexts/default/apps/my-awesome-app`
- installs the application from `~/.backplane/contexts/default/apps/my-awesome-app`

This mechanism is used by the `backplane` service running alongside Traefik and Portainer. This service enables you to `git push` to your **backplane**. Read more about this in the next paragraph.

**backplane app registry, default name**:

We're building a central registry for backplane-comtatible applications on [GitHub](https://github.com/backplane-apps). Installing one of those is as easy as running:

```bash
backplane install loki
```

- clones `https://github.com/backplane-apps/loki` to `~/.backplane/contexts/default/apps/loki`
- installs the application from `~/.backplane/contexts/default/apps/loki`

Our plan is to keep these apps compatible to Portainer's templating system to make them available as one-click installations from within the Portainer UI. One issue we currently face with this is that Portainer templates are only compatible with docker-compose configuration version "2". 

### With git

**backplane** contains a small Git Repository service with a dead-simple CI/CD workflow for your applications. The following section explains how to push your code to a remote **backplane** where it then will be automatically built and deployed according to the workflows described in the previous sections.

This might also make sense on local development machines, but is primarily meant as a method to deploy your applications to remote **backplane** hosts in a safe way. For the following parts we assume that you have a server somewhere in the internet that you have access to via SSH (public-key authentication) and you want to use **backplane** to deploy and run your Docker Compose services on that server.

Let's assume our remote **backplane** has the following attributes:

- ip: 1.2.3.4
- backplane-domain: 1-2-3-4.ns0.co
- https: enabled

> **ATTENTION**: the Git Repository service uses `~/.ssh` of the user that initialized **backplane** (i.e. `backplane init`) to determine the `authorized_keys` that are eligible to push to **backplane** via git. Make sure to add all relevant public keys to `~/.ssh/authorized_keys` on your **backplane** host

> **TIP**: `cat ~/.ssh/id_rsa.pub | pbcopy` copies your SSH public key to your clipboard

#### Update your ssh config

Add the following to your local `~/.ssh/config` file. This allows you to reach your remote **backplane** under `backplane` without further configuration.

```bash
Host backplane
    HostName 1.2.3.4
    User backplane
    Port 2222
```

**Wrapup**:

- our remote **backplane** (on 1.2.3.4) is now available as `backplane` when connecting with ssh
- **backplane** runs on port 2222; ports ins git remote-urls can cause problems which is why we *mask* port and ip behind the `backplane` hostname

> **NOTE**: replace the value of "HostName" with your server's IP or hostname. For convenience, we're using [ns0](https://ns0.co) here to provide wildcard DNS on IP basis

#### Update your git remote

Assuming your application repository is called `whoami`, this is how you add your remote **backplane** to your git remotes:

```bash
git remote add origin "git@backplane:whoami"
```

**Wrapup**:

- our previously configured remote **backplane** becomes our new git remote-url
- we're connecting as user `git`
- our repository on the remote it called `whoami`

#### Deploy to your server

> **HINT**: as you see, we're using the [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/) format here. This will likely be a part of backplane's future roadmap in the form of automated versioning based on commits. Just FYI.

```bash
git commit -am "feat: figured out who I am"
git push backplane master
```

That's it! **backplane** will build and deploy your application and expose it automatically as `https://whoami.1-2-3-4.ns0.co`.

## What is backplane

**backplane** consists of 3 main services running as Docker containers on your host:

- [Traefik](https://doc.traefik.io/traefik/), a very popular, cloud-native reverse-proxy
- [Portainer](https://www.portainer.io/), a very popular management interface for Docker
- [backplane](https://github.com/wearep3r/backplane), this software

It aims to provide simple access to core prerequisites of modern app development:

- Endpoint exposure
- Container management
- Deployment workflows

To develop and run modern web-based applications you need a few core ingredients, like a reverse-proxy handling request routing, a way to manage containers and a way to deploy your code. **backplane** offers this for local development as well as on production nodes in a seemless way.

**backplane** makes it easy to bypass long CI pipelines and deploy your application to a remote backplane host with ease.

**backplane** is mainly aimed at small to medium sized development teams or solo-developers that don't require complex infrastructure. Use it for rapid prototyping or simple deployment scenarios where the full weight of modern CI/CD and PaaS offerings just isn't bearable.

You can migrate from local development to production with a simple `git push` when using **backplane** on both ends. Think of it as a micro-PaaS that you can use locally.

## What backplane is NOT

- a PaaS solution; backplane only provides a well-configured reverse-proxy and a management interface for containers
- meant for production use. You can, though, but at your own risk

## Advanced configuration

**backplane** is only a thin wrapper around Traefik and Portainer. If you require more complex routing scenarios or have more complex service setups (e.g. multiple domains per container), simply use Traefik's label-based configuration.

[Read more](https://doc.traefik.io/traefik/) in the docs.

### Expose containers with non-standard ports

**backplane** expects your services to listen to port 80 inside their containers. If that is not the case, you need to tell the backplane about it. Add the following additional labels to tell backplane your service is accessible on port 9000:

```yaml
labels:
  - backplane.enabled=true
  - "traefik.http.services.custom-http.loadbalancer.server.port=9000"
```

## Examples

In the [examples](examples) directory you'll find examples showing how to integrate backplane with your existing services

Change to any of the example folders and run `backplane install`. The example's `README` will hold additional information on how to use it.

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

#### Build Docker

```bash
docker build -t wearep3r/backplane .
docker tag wearep3r/backplane wearep3r/backplane:$(backplane --version)
docker push wearep3r/backplane:$(backplane --version)
docker tag wearep3r/backplane wearep3r/backplane:latest
docker push wearep3r/backplane:latest
```

### Generate release

```bash
semantic-release version
```

### Publish release

```bash
semantic-release publish
```

## Author

Fabian Peter, [p3r.](https://www.p3r.one/)