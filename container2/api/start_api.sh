#!/bin/bash

# innovation-hub-api - container2 - api/start_app.sh
# written by: Andrew McDonald
# initial: 23/05/23
# current: 17/07/23
# version: 0.9

# monit watchdog gunicorn start/stop script
# referenced in /etc/monit/conf.d/gunicorn3.conf

PIDFILE=/var/run/gunicorn.pid
PROJECT_DIR=/home/innovation-hub-api/api/

case $1 in
        start)
                cd ${PROJECT_DIR}

                exec gunicorn3 -c gunicorn_config.py api:server > /dev/null 2>&1 &

                #echo $! > ${PIDFILE} # save spawned backround process' PID to PIDFILE
                #cat ${PIDFILE};;

        stop)
                cat ${PIDFILE}
                kill `cat ${PIDFILE}`
                rm ${PIDFILE};;
        *)
                echo "usage: $0 {start|stop}" ;;
esac
exit 0
