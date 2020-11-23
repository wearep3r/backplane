#!/bin/bash
set -e

if [ "$1" = "ssh" ];
then
  # Check if authorized_keys already exists
  if [ -f "/runner/.ssh/authorized_keys" ];
  then
    printf "\e[1;32m Found authorized keys in /runner/.ssh/authorized_keys.\e[0m\n"
  else
    if [ "$BACKPLANE_RUNNER_PUBLIC_KEY" != "" ];
    then
      printf "\e[1;32m Adding BACKPLANE_RUNNER_PUBLIC_KEY to /runner/.ssh/authorized_keys.\e[0m\n"
      echo "$BACKPLANE_RUNNER_PUBLIC_KEY" > /runner/.ssh/authorized_keys
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
  
