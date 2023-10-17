# innovation-hub-api - container2 - Dockerfile
# written by: Andrew McDonald
# initial: 23/05/23
# current: 17/07/23
# version: 0.9

# get base image
FROM debian:buster-slim

# set container maintainer
LABEL maintainer="andrew mcdonald <andrew.mcdonald@latrobe.edu.au>"

# add nuster backports repository
RUN printf "%s\n" "deb http://ftp.de.debian.org/debian buster-backports main" | \
    tee /etc/apt/sources.list.d/buster-backports.list

# install monit from buster backport repo
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update -y && \
    apt-get install -y -t buster-backports monit

# installations and clean up 
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y \
    python3 \
    rustc \
    python3-venv \
    python3-pip \
    build-essential \
    libssl-dev \
    python-dev \
    libffi-dev \
    python3-pymysql \
    gunicorn3 \
    procps \
    curl \
    wget \
    unzip \
    jq \
    lsof \
    tzdata \
    && rm -rf /var/lib/apt/lists/*
	
# Download and install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable

# set working directory
WORKDIR /

# copy script and then make executable
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
#RUN python3 -m pip install --upgrade pip setuptools wheel --no-warn-script-location && \
#    pip3 install -r requirements.txt --no-warn-script-location

# set app healthcheck
HEALTHCHECK --interval=120s --timeout=10s --start-period=60s \  
    CMD /healthcheck.sh

# run final init script
ENTRYPOINT ["/entrypoint.sh"]
