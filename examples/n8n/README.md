# n8n @ backplane

## Get started

This is based on the default `docker-compose.yml` from [n8n](https://github.com/n8n-io/n8n/blob/master/docker/compose/withPostgres/docker-compose.yml).

Run `docker-compose up`. Visit n8n at [http://n8n.127-0-0-1.ns0.co](http://n8n.127-0-0-1.ns0.co).

## Notes

- `n8n` runs on port 9000 5678 the container, thus additional labels for **Traefik** has been added to correctly establish the connection between the reverse-proxy and the container

```yaml
labels:
  - backplane.enabled=true
  - "traefik.http.routers.n8n.service=n8n"
  - "traefik.http.services.n8n.loadbalancer.server.port=5678"
```
