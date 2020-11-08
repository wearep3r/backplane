#!/usr/bin/env bash

set -eo pipefail
[[ $DEBUG ]] && set -x
set -o allexport

FPREFIX="=====>"
PREFIX="----->"
INDENT="      "

if [[ ! -x "$(command -v docker)" ]]; then
  echo "You must install Docker on your machine";
  return
fi

if [[ ! -x "$(command -v docker-compose)" ]]; then
  echo "You must install Docker Compose on your machine";
  return
fi

getIP() {
  declare cmd="getIP"
  [[ "$1" == "$cmd" ]] && shift 1

  if [[ $(uname) == "Darwin" ]]; then
    ip=$(ipconfig getifaddr en0)
  else
    ip=$(ip -o route get to 8.8.8.8 | sed -n 's/.*src \([0-9.]\+\).*/\1/p')
  fi
  
  echo $ip
}

getDomain() {
  declare cmd="getDomain"
  [[ "$1" == "$cmd" ]] && shift 1

  ip=$(getIP)
  domain=${DOMAIN:-${ip}.xip.io}
  echo $domain
}

updateConfig() {
  #sed -i '' "s/DOMAIN=*/DOMAIN=$domain/g" {.env}
  echo "222"
}

deploy() {
  declare cmd="deploy"
  [[ "$1" == "$cmd" ]] && shift 1

  environment=$1

  echo $environment

  if [ "$environment" == "" ]; then
    echo "No environment chosen; select either 'local' or 'public'"
    exit 1
  fi


  ENV_FILE="environments/$environment/.env"
  COMPOSE_FILE="environments/$environment/docker-compose.yml"

  echo "$PREFIX Starting deployment"
  echo "$INDENT Command: $@"
  echo "$INDENT Compose File: $COMPOSE_FILE"

  if [[ -f $ENV_FILE ]]; then
    set -o allexport
    source "$ENV_FILE"
    set +o allexport
  fi

  if [[ -f $COMPOSE_FILE ]]; then
    COMPOSE_CONFIG=$(docker-compose config)
    echo "$PREFIX Deploying Backplane"
    command=$(docker-compose --file "$COMPOSE_FILE" --project-name "backplane" up -d)
    
    echo "$FPREFIX Backplane deployed:"
  else
    echo "$PREFIX No docker-compose.yml found at $COMPOSE_FILE, exiting"
    exit 1
  fi
}

logs() {
  declare cmd="logs"
  [[ "$1" == "$cmd" ]] && shift 1

  environment=$1

  ENV_FILE="environments/$environment/.env"
  COMPOSE_FILE="environments/$environment/docker-compose.yml"

  [[ "$1" == "$environment" ]] && shift 1

  service=$1

  echo "$PREFIX Starting logs"
  echo "$INDENT Environment: $environment"
  echo "$INDENT Service: ${service:-all}"

  if [[ -f $COMPOSE_FILE ]]; then
    if [ "$service" == "" ]; then
      command=$(docker-compose --file "$COMPOSE_FILE" --project-name "backplane" logs -f)
    else
      command=$(docker-compose --file "$COMPOSE_FILE" --project-name "backplane" logs -f $service)
    fi
  else
    echo "$PREFIX No docker-compose.yml found at $COMPOSE_FILE, exiting"
    exit 1
  fi
}

"$@"