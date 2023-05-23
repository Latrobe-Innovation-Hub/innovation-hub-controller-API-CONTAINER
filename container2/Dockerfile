# HiveKeepers - container2 - Dockerfile
# written by: Andrew McDonald
# initial: 28/01/22
# current: 17/03/22
# version: 0.9

# get base image
FROM debian:stable-slim

# set container maintainer
LABEL maintainer="andrew mcdonald <andrewm.mcdonald@latrobe.edu.au>"

# installations and clean up 
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update -y && \
    apt-get install -y \
    python3 \
    python3-pip \
    sqlite3 \
    python3-pymysql \
    gunicorn3 \
    procps \
    monit \
    curl \
    lsof \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# set working directory
WORKDIR /

# copy script and make executable
COPY docker-entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

# copy service healthcheck
# dash    -> done
COPY healthcheck.sh healthcheck.sh
RUN chmod +x healthcheck.sh

# create logging directory
RUN mkdir -p /home/innovation-hub-api/logs

WORKDIR /etc/monit
COPY ./monit/monitrc .
RUN chmod 700 monitrc
COPY ./monit/gunicorn3.conf conf.d/gunicorn3.conf

# set working directory
WORKDIR /home/innovation-hub-api/

# copy Dash application folder
COPY api /home/innovation-hub-api/api

# update user app file permissions for user
RUN chmod -R 664 /home/innovation-hub-api && \
    chmod +x /home/innovation-hub-api/api/start_api.sh

# set working directory
WORKDIR /home/innovation-hub-api/api

# update pip,etc and install python app requirements
RUN python3 -m pip install --upgrade pip setuptools wheel --no-warn-script-location && \
    pip3 install -r requirements.txt --no-warn-script-location

# set app healthcheck
HEALTHCHECK --interval=120s --timeout=10s --start-period=60s \  
    CMD /healthcheck.sh

# run final init script
ENTRYPOINT ["/entrypoint.sh"]
