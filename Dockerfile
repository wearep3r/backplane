ARG DOCKER_VERSION=19.03.13

FROM docker:${DOCKER_VERSION} AS docker-cli

FROM ubuntu:latest

ARG COMPOSE_VERSION=1.27.4

RUN apt-get update && apt-get install --no-install-recommends openssh-server curl git sudo python3-pip apache2-utils -y \
    && pip3 install "docker-compose${COMPOSE_VERSION:+==}${COMPOSE_VERSION}" poetry

# Tooling
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

ARG HELM_VERSION=3.4.1
ARG KUBECTL_VERSION=1.19.0

RUN echo "curl -fsSL -o helm.tar.gz https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" \
    && curl -fsSL -o helm.tar.gz https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz \
    && tar xfvz helm.tar.gz \
    && mv linux-amd64/helm /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm \
    && rm -rf linux-amd64

RUN curl -L https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl -o kubectl \
    && mv kubectl /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl

# Directories
RUN mkdir -p /app /backplane/repositories /backplane/hooks /backplane/deployments \
    && chown 1000:1000 /backplane -R

WORKDIR /app

COPY poetry.lock pyproject.toml README.md CHANGELOG.md /app/

RUN poetry config virtualenvs.create false \
    && poetry install -n --no-root

COPY . /app/

RUN poetry install

RUN useradd -rm -d /backplane -s /bin/bash -g root -G sudo -u 1001 git \
    && usermod -aG root git \
    && groupadd -g 1000 docker \
    && useradd -g docker -u 1000 docker \
    && echo "git:git" | chpasswd

RUN mkdir -p /backplane/.ssh/ \
    && touch /backplane/.ssh/known_hosts \
    && chown git:root /backplane -R

COPY build/config/ssh_config /etc/ssh/ssh_config
COPY build/config/sshd_config /etc/ssh/sshd_config
COPY build/scripts/backplane-ssh /usr/local/bin/backplane-ssh
COPY build/hooks/post-receive /backplane/hooks/post-receive
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# # Install Poetry
# RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python && \
#     cd /usr/local/bin && \
#     ln -s /opt/poetry/bin/poetry && \
#     poetry config virtualenvs.create false

# # Copy poetry.lock* in case it doesn't exist in the repo
# COPY ./pyproject.toml ./poetry.lock* /app/

# # Allow installing dev dependencies to run tests
# ARG INSTALL_DEV=false
# RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --no-dev ; fi"

RUN echo 'PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin"' >> /backplane/.profile \
    && echo "git ALL=NOPASSWD:ALL" >> /etc/sudoers

RUN chmod +x /usr/local/bin/backplane-ssh /backplane/hooks/post-receive /usr/local/bin/docker-entrypoint.sh

ENV DOCKER_HOST=unix:///var/run/docker.sock

RUN backplane init --no-docker

EXPOSE 2222

ARG BUILD_DATE
ARG VCS_REF
ARG BUILD_VERSION
 
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
 
CMD ["/bin/bash", "-c"]

LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.name="wearep3r/backplane"
LABEL org.label-schema.description="A dead-simple backplane for your Docker Compose services"
LABEL org.label-schema.url="http://backplane.sh/"
LABEL org.label-schema.vcs-url="https://github.com/wearep3r/backplane"
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.vendor="wearep3r"
LABEL org.label-schema.version=$BUILD_VERSION