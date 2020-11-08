# backplane

A simple backplane for your containerized applications.

- [Traefik](https://doc.traefik.io/traefik/getting-started/quick-start/) reverse-proxy for your containers
- [Portainer](https://www.portainer.io/) management dashboard for Docker

## Get started

```bash
git clone https://gitlab.com/p3r.one/backplane $HOME/.backplane
cd $HOME/.backplane
docker-compose --project-name backplane up -d
```

You can now visit the dashboards of both services in your browser:

- [Traefik Dashboard](http://traefik.here.ns0.co)
- [Portainer Dashboard](http://portainer.here.ns0.co)

To expose one of your services through Traefik, your service needs to be part of the `backplane` Docker network and carry a few Traefik-relevant labels:

```bash
portainer:
  image: portainer/portainer-ce:2.0.0
  container_name: portainer
  command: -H unix:///var/run/docker.sock
  restart: unless-stopped
  security_opt:
    - no-new-privileges:true
  networks:
    - backplane
  volumes:
    - "/var/run/docker.sock:/var/run/docker.sock:ro"
    - "portainer-data:/data"
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.portainer.entrypoints=http"
    - "traefik.http.routers.portainer.rule=Host(`portainer.${BACKPLANE_DOMAIN}`)"
    - "traefik.http.routers.traefik.middlewares=compress@file"
    - "traefik.http.routers.portainer.service=portainer"
    - "traefik.http.services.portainer.loadbalancer.server.port=9000"
    - "traefik.docker.network=backplane"
```