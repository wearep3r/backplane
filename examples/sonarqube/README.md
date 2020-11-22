# Sonarqube @ backplane

## Get started

This is based on the default `docker-compose.yml` from [Sonarsource's Sonarqube](https://github.com/SonarSource/docker-sonarqube).

Run `docker-compose up`. Visit Sonarqube at [http://sonaqube.127-0-0-1.ns0.co](http://sonaqube.127-0-0-1.ns0.co).

## Notes

- `sonarqube` runs on port 9000 inside the container, thus additional labels for **Traefik** has been added to correctly establish the connection between the reverse-proxy and the container

```yaml
labels:
  - backplane.enabled=true
  - "traefik.http.routers.sonarqube.service=sonarqube"
  - "traefik.http.services.sonarqube.loadbalancer.server.port=9000"
```

## Authentication

To hook up to your backplane's authentication system, add the following to your `docker-compose.yml`:

```yaml
labels:
  - "traefik.http.routers.sonarqube.middlewares=auth@docker"
```
