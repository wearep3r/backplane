#!/bin/bash
set -e

DOCKER_SOCKET=/var/run/docker.sock
DOCKER_GROUP=docker
BUILD_USER=git

echo "Adding hosts GID to docker system group"

if [ -S ${DOCKER_SOCKET} ]; then
    DOCKER_GID=$(stat -c '%g' ${DOCKER_SOCKET})

    GROUP_NAME=$(cut -d: -f1 < <(getent group $DOCKER_GID))

    if [ "$GROUP_NAME" != "" ];
    then
      echo "Group $GROUP_NAME exists. Adding user ..."
      addgroup  ${BUILD_USER} ${GROUP_NAME} || true
    else
      addgroup --system --gid ${DOCKER_GID} ${DOCKER_GROUP} || true
      addgroup  ${BUILD_USER} ${DOCKER_GROUP} || true
    fi
fi

if [ "$1" = "ssh" ];
then
  # Check if authorized_keys already exists
  if [ -f "/backplane/.ssh/authorized_keys" ];
  then
    printf "\e[1;32m Found authorized keys in /backplane/.ssh/authorized_keys.\e[0m\n"
  else
    if [ "$BACKPLANE_RUNNER_PUBLIC_KEY" != "" ];
    then
      printf "\e[1;32m Adding BACKPLANE_RUNNER_PUBLIC_KEY to /backplane/.ssh/authorized_keys.\e[0m\n"
      echo "$BACKPLANE_RUNNER_PUBLIC_KEY" > /backplane/.ssh/authorized_keys
    else
      printf "\e[1;31m BACKPLANE_RUNNER_PUBLIC_KEY is empty. Terminating.\e[0m\n"
      exit 1
    fi
  fi
  
    
  service ssh start  > /dev/null
  service ssh status  > /dev/null

  if [ "$?" = "0" ];
  then
    printf "\e[1;32m Started SSH server.\e[0m\n"
    tail -f /dev/null
  else
    printf "\e[1;31m Failed to start SSH server. Terminating.\e[0m\n"
    exit 1
  fi
else
  exec "$@"
fi
  
