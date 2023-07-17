#!/bin/bash

# innovation-hub-api-container - container1 - docker-entrypoint.sh
# written by: Andrew McDonald
# initial: 23/05/23
# current: 17/07/23
# version: 0.9

set -e

# set log locations
container_log=/home/innovation-hub-api/persistent/logs/container1/entrypoint.log
nginx_access_log=/home/innovation-hub-api/persistent/logs/container1/nginx-access.log
nginx_error_log=/home/innovation-hub-api/persistent/logs/container1/nginx-error.log
fail2ban_log=/home/innovation-hub-api/persistent/logs/container1/fail2ban.log
monit_log=/home/innovation-hub-api/persistent/logs/container1/monit.log

if [[ ! -d /home/innovation-hub-api/persistent/logs/container1 ]]
    then
      mkdir -p /home/innovation-hub-api/persistent/logs/container1
fi

# make sure log file exists
touch $container_log

echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] === STARTING CONTAINER1 ===" | tee -a $container_log

user=$(whoami)
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] ----------- USER ID: " $(id $user) | tee -a $container_log

# get relevant environment variables, otherwise use defaults
proxy_log_level=${PROXY_LOG_LEVEL:-simple}
proxy_log_level_lower=${log_level,,}
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] user passed proxy logging level: " $proxy_log_level_lower | tee -a $container_log

nginx_log_level=${NGINX_ERROR_LOG_LEVEL}
nginx_log_level_lower=${nginx_log_level,,}
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] user passed nginx error logging level: " $nginx_log_level_lower | tee -a $container_log

app_proxy_port=${APP_PORT:-8050}
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] user passed app port: " $app_proxy_port | tee -a $container_log

## set up nginx reverse proxy access
if [ -s /scripts/password_script.sh ]; then
    if [ -f /scripts/user_credentials.txt ]; then
        if [ -s /scripts/user_credentials.txt ]
          then
            echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] found password script." | tee -a $container_log
            echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] found user credentials text file." | tee -a $container_log
            echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] user credentials text file is populated!" | tee -a $container_log
            echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] creating user credentials for proxy..." | tee -a $container_log

            ## run user password create script
            /bin/bash /scripts/password_script.sh /scripts/user_credentials.txt

            echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] deleting user credentials text file..." | tee -a $container_log

            ## delete plain-text user passwords file
            rm /scripts/user_credentials.txt

            if [ ! -f user_credentials.txt ]
              then
                echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] user credentials text file deleted" | tee -a $container_log
              else
                echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] [ERROR] user credentials text file not deleted!" | tee -a$container_log
            fi
          else
            echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] user credentials text file is empty" | tee -a $container_log
        fi
    fi
fi

# set password:username delimter, :
FS=":"

# log users with proxy access
while read line || [ -n "$line" ];
do
  # print user log access
  NAME=$(echo $line|cut -d$FS -f1)
  echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] ACCESS CREDENTIALS FOUND FOR USER: " $NAME | tee -a $container_log
done < /etc/nginx/auth/.htpasswd

## run nginx env setup script
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] running nginx envsubstitution template script..." | tee -a $container_log
/bin/bash /docker-entrypoint.d/20-envsubst-on-templates.sh

# make sure log files exist
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] making sure log files exist" | tee -a $container_log
touch $nginx_access_log
touch $nginx_error_log
touch $fail2ban_log
touch $monit_log

## setup fail2ban ip banning service
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] setting up fail2ban service..." | tee -a $container_log
rm -f /var/run/fail2ban/*

## start fail2ban
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] starting fail2ban service..." | tee -a $container_log
service fail2ban start

# set fail2ban log level
#fail2ban-client set loglevel $fail2ban_log_level

# flush fail2ban log if a file
#fail2ban-client flushlogs

## == fail2ban info commands ==
## fail2ban-client get nginx-http-auth banned     # return banned IPs
## fail2ban-client get nginx-http-auth findtime   # gets the time for which the filter will look back for failures
## fail2ban-client get nginx-http-auth bantime    # gets the time a host is banned for
## fail2ban-client get nginx-http-auth maxretry   # gets the number of failures allowed before ban

## start nginx reverse proxy service
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] starting nginx proxy service..." | tee -a $container_log
nginx

## start Monit monitoring service
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] starting Monit monitoring service..." | tee -a $container_log
/etc/init.d/monit start

# start tail of service logs
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] tailing nginx and fail2ban service logs..." | tee -a $container_log
exec tail -f $nginx_access_log $nginx_error_log $monit_log $fail2ban_log


#if [ "$proxy_log_level_lower" == "simple" ]
#  then
#    echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] setting service logs tail verbosity to: simple" | tee -a $container_log
#    exec tail -f $nginx_error_log $fail2ban_log $monit_log
#elif [ "$proxy_log_level_lower" == "detailed" ]
#  then
#    echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] setting service logs tail verbosity to: detailed" | tee -a $container_log
#    exec tail -f $nginx_access_log $nginx_error $fail2ban_log $monit_log
#else # set simple by default
#  echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] setting service logs tail verbosity to default: simple" | tee -a $container_log
#  exec tail -f $nginx_error_log $fail2ban_log $monit_log
#fi
