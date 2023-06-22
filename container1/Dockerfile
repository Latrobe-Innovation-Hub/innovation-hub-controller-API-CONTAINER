# innovation-hub-api-container - container1 - Dockerfile
# written by: Andrew McDonald
# initial: 23/05/23
# current: 23/05/23
# version: 0.9

# get base image
FROM nginx:1.20.2

# set container maintainer
LABEL maintainer="andrew mcdonald <andrew.mcdonald@latrobe.edu.au>"

# installations and clean up
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update -y && \
    apt-get install -y \
    fail2ban \
    iptables \
    whois \
    apache2-utils \
    monit \
    lsof \
    procps \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# copy nginx configuration files
WORKDIR /etc/nginx
COPY ./nginx/nginx.conf .
COPY ./nginx/templates templates/

# copy nginx env substitution script
COPY fixed_envsubst-on-templates.sh /docker-entrypoint.d/20-envsubst-on-templates.sh
RUN chmod +x /docker-entrypoint.d/20-envsubst-on-templates.sh

# create dir for basic-auth file .htpasswd and set user access
RUN mkdir -p auth && \
    touch auth/.htpasswd

# add basic hivekeeper root web page
WORKDIR /var/www/html
#COPY ./nginx/html/index.html .
#COPY ./nginx/html/background.jpg .
COPY ./nginx/html .

# copy fail2ban local/docker configurations
WORKDIR /etc/fail2ban
COPY ./fail2ban/jail.local .
COPY ./fail2ban/fail2ban.local .
COPY ./fail2ban/action.d/docker-iptables-multiport.conf ./action.d
COPY ./fail2ban/filter.d/nginx-http-auth.conf ./filter.d
COPY ./fail2ban/jail.d/nginx.conf ./jail.d

# create log folder for sshd jail - prevents sshd jail log error
RUN touch /var/log/auth.log  && \
    mkdir -p /var/run/fail2ban && \
    touch /var/run/fail2ban/fail2ban.pid

# setup service monitoring with Monit
WORKDIR /etc/monit
COPY ./monit/monitrc .
COPY ./monit/nginx.conf conf.d/nginx.conf
COPY ./monit/fail2ban.conf conf.d/fail2ban.conf

RUN chmod 0700 monitrc

# copy fixed nginx-docker ENV substition template script
RUN mkdir -p /scripts
WORKDIR /scripts

# copy password script
COPY password_script.sh .
RUN chmod +x password_script.sh 

# copy user credentials file for access
# make and store this file within container1/ if you want to bake in user password
# access into the base image created by this Dockerfile.
# text file structure is: user:password (per line)
#   eg:
#       user1:password1
#       user2:password2
#       user3:password3
#       ...
# NOTE: cannot be used if passing .htpasswd file in via docker-compose.yaml file
#
COPY user_credentials.txt .
#
# set permissions for scripts
RUN chmod +x password_script.sh

# change back to root /
WORKDIR /

# service healthchecks
# nginx    -> done
# fail2ban -> done
COPY healthcheck.sh .
RUN chmod +x healthcheck.sh

# copy init script
COPY docker-entrypoint.sh entrypoint.sh

RUN chmod +x entrypoint.sh

# run healthcheck
HEALTHCHECK --interval=120s --timeout=10s --start-period=60s \  
    CMD /healthcheck.sh

# run final init script
ENTRYPOINT ["/entrypoint.sh"]
