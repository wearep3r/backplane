#!/bin/bash
set -e
  
printf "\n\033[0;44m---> Starting the SSH server.\033[0m\n\n"
  
service ssh start
service ssh status

printf "\n\033[0;44m---> Adding BACKPLANE_RUNNER_PUBLIC_KEY to authorized_keys file.\033[0m\n"

if [ "$BACKPLANE_RUNNER_PUBLIC_KEY" != "" ];
then
  echo "$BACKPLANE_RUNNER_PUBLIC_KEY" > /runner/.ssh/authorized_keys
else
  echo "PUBLIC_KEY is empty. Terminating."
  exit 1
fi
  
exec "$@"