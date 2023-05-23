#!/bin/bash

# innovation-hub-api - container2 - healthycheck.sh
# written by: Andrew McDonald
# initial: 23/05/23
# current: 23/05/23
# version: 0.9

# this script runs simple health check on
# Dash container service.
# returns 0 if healthy, 1 if unhealthy

# check Dash status and return docker health status
if [[ $(curl -s http://localhost:$API_PORT/ping) == "{status: ok}" ]]
  then
    echo 0
  else
    echo 1
fi
