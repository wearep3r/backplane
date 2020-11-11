FROM linuxserver/openssh-server

RUN apk update && apk add git

RUN mkdir -p /runner/repositories /runner/hooks /runner/deployments \
  && chown 1000:1000 /runner -R

COPY backplane-ssh /usr/local/bin/backplane-ssh
COPY backplane-runner /usr/local/bin/backplane-runner
COPY post-receive /runner/hooks/post-receive

RUN chmod +x /usr/local/bin/backplane-ssh /usr/local/bin/backplane-runner /runner/hooks/post-receive