#!/bin/bash

# HiveKeepers - container1 - healthycheck.sh
# written by: Andrew McDonald
# initial: 25/02/22
# current: 17/03/22
# version: 0.9

# this script runs simple health checks on
# nginx and fail2ban container services.
# returns 0 if healthy, 1 if unhealthy

# init service status variables
NGINX_STATUS=-1
FAIL2BAN_STATUS=-1
MONIT_STATUS=-1

# check nginx status and update status var
if [ $(curl -s -o /dev/null -w "%{http_code}" localhost/healthcheck) == 200 ]
  then
    NGINX_STATUS=0
  else
    NGINX_STATUS=1
fi

# get monit service status
MONIT_NGINX=$(monit summary | grep nginx | awk '{ print $2 }')
MONIT_FAIL2BAN=$(monit summary | grep fail2ban | awk '{ print $2 }')

# update monit service status
if [[ "$MONIT_NGINX" == "OK" ]]
  then
    MONIT_NGINX=0
  else
    MONIT_NGINX=1
fi

# update monit service status
if [[ "$MONIT_FAIL2BAN" == "OK" ]]
  then
    MONIT_FAIL2BAN=0
  else
    MONIT_FAIL2BAN=1
fi

# get overall monit service status
if [[ $MONIT_NGINX == 0 && $MONIT_FAIL2BAN == 0 ]]
  then
    MONIT_STATUS 0
  else
    MONIT_STATUS 1
fi

# check fail2ban status and update status var
if [[ $(fail2ban-client ping) == "Server replied: pong" ]]
  then
    FAIL2BAN_STATUS=0
  else
    FAIL2BAN_STATUS=1
fi

# check all status vars and return docker health status
if [[ $NGINX_STATUS == 0 && $FAIL2BAN_STATUS == 0 && $MONIT_STATUS == 0 ]]
  then
    echo 0
  else
    echo 1
fi
