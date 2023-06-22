#!/bin/bash

# innovation-hub-api - container2 - docker-entrypoint.sh
# written by: Andrew McDonald
# initial: 23/05/23
# current: 23/05/23
# version: 0.9

set -e

# get container choices - with defaults
START="${START_TYPE:-Warm_Start}"
user=$(whoami)
cores=$(nproc --all)
workers="${APP_WORKERS:-$cores}"
port="${APP_PORT:-8050}"

threads_default=$(($cores - 1))
threads="${APP_THREADS:-$threads_default}"

log_level=${APP_LOG_LEVEL:-info}
log_level_lower=${log_level,,}

# set log locations
container_log=/home/innovation-hub-api/persistent/logs/container2/entrypoint.log
gunicorn_log=/home/innovation-hub-api/persistent/logs/container2/gunicorn.log
gunicorn_access_log=/home/innovation-hub-api/persistent/logs/container2/gunicorn-access.log
monit_log=/home/innovation-hub-api/persistent/logs/container2/monit.log

# the local database file location
local_database=/home/innovation-hub-api/persistent/db/innovation-hub-api.db

# if persistent log location doesn't exist, make it!
if [[ ! -d /home/innovation-hub-api/persistent/logs/container2 ]]
    then
      mkdir -p /home/innovation-hub-api/persistent/logs/container2
fi

# make sure log file exists
touch $container_log

# log container info
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] === STARTING CONTAINER2 ===" | tee -a $container_log
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] start type: " $START | tee -a $container_log
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] USER ID: " $(id $user) | tee -a $container_log
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] number of cores found: " $cores | tee -a $container_log
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] setting gunicorn workers: " $workers | tee -a $container_log
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] setting gunicorn threads: " $threads | tee -a $container_log
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] setting gunicorn listening port: " $port | tee -a $container_log
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] setting application logging level: " $log_level_lower | tee -a $container_log

start_api() {
  # check if files exist and have content
  if [ -s /home/innovation-hub-api/api/api.py ]
    then
      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] api.py is populated!" | tee -a $container_log
      cd /home/innovation-hub-api/api/

      # update pip
      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] updating python setuptools, wheels..." | tee -a $container_log
      python3 -m pip install --upgrade pip setuptools wheel --no-warn-script-location

      # install app requirements
      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] installing python requirements..." | tee -a $container_log
      pip3 install -r requirements.txt --no-warn-script-location --break-system-packages

      # start api via wsgi (gunicorn)
      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] starting application dashboard..." | tee -a $container_log
      # gunicorn3 hivekeepers_app:server \
      # --bind 0.0.0.0:$port \
      # --workers $workers \
      # --worker-tmp-dir /dev/shm \
      # --threads $threads \
      # --log-level=$log_level_lower \
      # --access-logfile=- \
      # --log-file=$gunicorn_log \
      # --error-logfile=$gunicorn_error_log \
      # --access-logfile=$gunicorn_access_log

      # using config for gunicorn allows for easier monit monitoring via PID file and dash_app/start_app.sh
      gunicorn3 -c gunicorn_config.py api:app

    else
      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] [ERROR] api.py is NOT populated!" | tee -a $container_log
      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] NOT starting api!" | tee -a $container_log
  fi
}

#build_local_database() {
#  if [[ ! -d /home/innovation-hub-api/persistent/db ]]
#    then
#      mkdir -p /home/innovation-hub-api/persistent/db
#  fi
#
#  # build local db from remote source
#  if [[ ! -f $local_database ]]
#    then
#      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] building database..." | tee -a $container_log
#
#      # no local database found, do initial build from remote db
#      touch $local_database
#      python3 startup_update_db.py
#
#    else
#      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] database found!" | tee -a $container_log
#      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] checking for database updates..." | tee -a $container_log
#
#      # local database found, check for updates from remote db
#      db_update_status=$(python3 update_db.py)
#
#      echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] "$db_update_status | tee -a $container_log
#  fi
#}

tail_logs () {
  echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] setup tailing of api log" | tee -a $container_log
  if [[ "$1" == "async" ]]
    then
      tail -f $gunicorn_log \
              $gunicorn_access_log \
              $monit_log &
    else
      tail -f $gunicorn_log \
              $gunicorn_access_log \
              $monit_log
  fi
}

touch_logs () {
  echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] making sure log files exist" | tee -a $container_log
  touch $gunicorn_log
  touch $gunicorn_access_log
  touch $monit_log
}

#clear_storage () {
#  # make sure the file exists, to prevent error when del a non-existent file
#  touch $local_database
#
#  echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] deleting database file" | tee -a $container_log
#  rm $local_database
#}

start_watchdog() {
  # reset the gunicorn config file in case of gunicorn port changes - replaces ln 12 back to original
  echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] resetting gunicorn3.conf..." | tee -a $container_log
  awk 'NR==12 {$0="  if failed host 127.0.0.1 port 8050 protocol http request '/ping' for 3 cycles then restart"} 1' /etc/monit/conf.d/gunicorn3.conf > /etc/monit/conf.d/gunicorn3.temp
  mv /etc/monit/conf.d/gunicorn3.temp /etc/monit/conf.d/gunicorn3.conf

  # update watchdog gunicorn conf port - sed inplace
  echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] updating watchdog port in gunicorn3.conf to: ${APP_PORT:-8050}" | tee -a $container_log
  sed -i "/^  if failed/ s/8050/${APP_PORT:-8050}/" /etc/monit/conf.d/gunicorn3.conf

  ## start Monit monitoring service
  echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER1] starting Monit monitoring service..." | tee -a $container_log
  /etc/init.d/monit start
}

# cd into app dir
echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] changing to dir: /home/innovation-hub-api/api" | tee -a $container_log
cd /home/innovation-hub-api/api/

#if [[ "$START" == "Cold_Start" ]]
#  then
#    # start container, flush dns, clear storage, retain logs, start application
#    echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] starting Cold_Start..." | tee -a $container_log
#    clear_storage
#    touch_logs
#    tail_logs "async"
#    start_watchdog
#    start_application
#elif [[ "$START" == "Warm_Start" ]]
#  then
#    # start container, start application
#    echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] starting Warm_Start..." | tee -a $container_log
#    touch_logs
#    tail_logs "async"
#    build_local_database
#    start_watchdog
#    start_application
#elif [[ "$START" == "Init_only" ]]
# then
#    # start container, not application
#    echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] starting Init_only..." | tee -a $container_log
#    clear_storage
#    touch_logs
#    tail_logs "async"
#fi

echo $(date +"%Y-%m-%d %H:%M:%S") "[CONTAINER2] starting Cold_Start..." | tee -a $container_log
#clear_storage
touch_logs
tail_logs "async"
start_watchdog
start_api

"$@"
