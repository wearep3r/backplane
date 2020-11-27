
FROM ubuntu:latest

RUN apt update && apt install --no-install-recommends openssh-server curl git sudo python3-pip apache2-utils -y \
    && pip3 install docker-compose poetry

RUN mkdir -p /app /backplane/repositories /backplane/hooks /backplane/deployments \
    && chown 1000:1000 /backplane -R

WORKDIR /app

COPY poetry.lock pyproject.toml README.md CHANGELOG.md /app/

RUN poetry config virtualenvs.create false \
    && poetry install -n --no-root

COPY . /app/

RUN poetry install

RUN useradd -rm -d /backplane -s /bin/bash -g root -G sudo -u 1000 git \
    && usermod -aG root git \
    && echo "git:git" | chpasswd

RUN mkdir -p /backplane/.ssh/ \
    && touch /backplane/.ssh/known_hosts \
    && chown git:root /backplane -R

COPY build/config/ssh_config /etc/ssh/ssh_config
COPY build/config/sshd_config /etc/ssh/sshd_config
COPY build/scripts/backplane-ssh /usr/local/bin/backplane-ssh
#COPY backplane-runner /usr/local/bin/backplane-runner
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

# Labels.
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.name="wearep3r/backplane"
LABEL org.label-schema.description="A dead-simple backplane for your Docker Compose services"
LABEL org.label-schema.url="http://backplane.sh/"
LABEL org.label-schema.vcs-url="https://github.com/wearep3r/backplane"
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.vendor="wearep3r"
LABEL org.label-schema.version=$BUILD_VERSION
 
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
 
CMD tail -f /dev/null

    