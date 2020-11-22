# Wordpress @ backplane

## Get started

This is based on the default `docker-compose.yml` from [bitnami's wordpress](https://github.com/bitnami/bitnami-docker-wordpress). 

Run `docker-compose up`. Visit Wordpress at [http://wordpress.127-0-0-1.ns0.co](http://wordpress.127-0-0-1.ns0.co).

## Notes

- to hook up to the `backplane` network while keeping the stack's internal networking intact, we need to specifically define a network `wordpress` for this stack as the `default` network won't be created due to the `backplane` network being invoked by a service
