# Innovation Hub Device Control API

---

pull to local via:
```bash
git clone --single-branch --branch master https://github.com/Hololens-Latrobe-Cisco/innovation-hub-api-container.git
```

---

### System Info
**names:**  
container1: reverse-proxy  
container2: api 
  
**services:**  
container1: nginx, fail2ban, monit   
container2: Flask (Python), Gunicorn, monit   
  
**container network:**  
subnet: 172.75.0.0/16   
container1 ip: 172.75.0.2   
container2 ip: 172.75.0.3   
  
**container persistent storage:**  
name: container_data:  
stores: logs (both containers), database (container1)  
container bind directory: /home/innovation-hub-api/persistent/  
  
**container1 persistent storage:**  
logs: /home/innovation-hub-api/persistent/logs/container1  
  
**container2 persistent storage:**  
logs: /home/innovation-hub-api/persistent/logs/container2
  
**Default API Access (through proxy; can be changed/removed):**  
Username: admin  
Password: admin

---

**Software Versions**  
container1:
  
| service            | source                        | version       |
| ------------------ | ----------------------------- | ------------- |
| Docker base Image  | Docker Hub (NGINX official)   | nginx:1.20.2  |
| NGINX              | Baked into base image         | 1.20.2        |
| Fail2ban           | Debian repository             | 0.11.2        |
| Monit              | Debian repository             | 5.27.2        |
  
container2:
  
| service            | source                        | version             |
| ------------------ | ----------------------------- | ------------------- |
| Docker base Image  | Docker Hub (Debian official)  | debian:stable-slim  |
| Pyython            | Debian repository             | 3.9.2               |
| SQLite             | Debian repository             | 3.34.1              |
| Gunicorn3          | Debian repository             | 20.1.0              |
| Monit              | Debian repository             | 5.27.2              |
  
---

**Environment Variables:**  
container1:

|                          |        |                                                                                             |
| ------------------------ | ------ | ------------------------------------------------------------------------------------------- |
| APP_PORT                 | INT    | Port to proxy to on container2, must match in both containers (defaults to 8050 if not set) |
| PROXY_LOG_LEVEL          | STRING | options: simple (no nginx access logging), detailed (with nginx access logging)             |
| NGINX_ERROR_LOG_LEVEL    | STRING | options: info, notice, warn, error, crit, alert, emerg (case sensitive)                     |
  
To get fail2ban to work with iptables requires container privilege capabilities to be used:  
```bash
cap_add:
  - CAP_NET_ADMIN
  - CAP_NET_RAW
```
  
container2:

|                          |        |                                                                                                   |
| ------------------------ | ------ | ------------------------------------------------------------------------------------------------- |
| APP_WORKERS              | INT    | Gunicorn workers - defaults to number of cores                                                    |
| APP_THREADS              | INT    | Gunicorn threads - defaults to number of cores – 1                                                |
| APP_PORT                 | INT    | listening port for Gunicorn WSGI, must match in both containers (defaults to 8050 if not set)     |
| APP_LOG_LEVEL            | STRING | options: debug, info, warning, error, critical                                                    |

---

**For further explanation of each container settings see relevant file for comments:**  
docker-compose.yamp - container start, env, and runtime settings: storage, networking  
Dockerfile - for image build settings  
docker-entryfile.sh - for runtime start process, services, file management, logging  
healthcheck.sh - for docker healtcheck status request response  
  
**See relevent container sub-dir for releveant service configurations**  
/monit - for watchdog service  
/nginx - for proxy service  
/fail2ban -  for authentification ip banning service  
/api - for python flask api application service  

---

### Container Roles
**Container1**  
Container1 handles all incoming network requests to the container network, and proxies any permissible requests destined for container2 to its respective static IP address.  
  
To handle incoming requests, container1 runs the NGINX service on port 80.  To control access to the container network, NGINX has basic-auth turned on and references a user:password file (.htpasswd) to determine relevant access privileges.  I Have made it so the password file can be created outside of the container and either passed in via the Dockerfile, or shared via a --volume -v in docker-compose.yaml
  
To handle requests that fail NGINX basic-auth 5 times, container1 also runs the service Fail2ban.  Fail2ban monitors the NGINX error log and records the IP address of failed access attempts to its log for future reference.  Once an IP address has reached 5 failed attempts within a given time span (10 mins) the IP address is banned from future access for 10 minutes – the number of attempts. the time frame for attempts, and the ban time can all be configured within Fail2bans configuration file before container1 build time if desired.  See authentification section for further explanation.  
  
Nginx only using port 80 currently - atm don't see any need for SSL, but that might change...  
  
Monit is used as the watchdog handler for monitoring the NGINX and Fail2ban services and restarts if either are found to be down/unresponsive.  
  
**Container2**  
Container2 runs the Innovation Hub API service whichi is written in Python.  The Web Server Gateway Interface (WSGI) Gunicorn is used to handle all web requests to and from the application.  
  
Contiainer2 has no exposed ports and is only accessible from outside the container network via the container1 reverse proxy.  

---

### Logging:

location: /home/innovation-hub-api/persistent/logs/container2
  
Log format: 'YYYY-MM-DD HH:MM:SS [SOURCE] [LEVEL] file.ext: message'  
Example: '2022-03-15 11:11:41,522 [PYTHON] [INFO] api.py: init app server...'  

**Log Options**
Logging level and detail/verbosity can be set for both containers within the docker-compose.yaml file.  
  
Container1:  
The container log level can be set system-wide for nginx and fail2ban services.  Available options are info, notice, warn, error, crit, alert, or emerg  
  
There is also the choice to log all NGINX access requests or to turn this feature off.  Available options are simple (no nginx access logging), or detailed (with nginx access logging).  
  
Container2:  
The container log level can be set system-wide for the Plotly Dash application and Gunicorn service.  Available options are debug, info, warning, error, or critical.  

---

### Watchdog Services:
**Container1:**  
Software: Monit  
Monitoring: NGINX, Fail2ban  
Web-monitor portal: Yes  
  
Monit is set up to monitor NGINX and Fail2ban services every 2mins and reports the status of each and handles service restart duties if they are found to be inactive.  Nginx is monitored via PID file and /healthcheck on port 80 Nginx that returns http code 200 on success; Fail2ban is monitored via PID file and socket.
  
Monit also provides a web port to both monitor and control system services.  This portal is located on port 2812 of container1, and access is provided via NGINX reverse proxy features.  
  
  To access Monit’s web portal, visit http://localhost/monit/
      **credentials:**  
          username: admin  
          password: admin  
  
Monit config files are stored in project dir: container1/monit/  
  
**Container2:**  
Software: Monit  
Monitoring: Gunicorn3  
Web-monitor portal: No  
  
Monit is set up to monitor the Guniicorn3 service every 2mins and reports the status and handles service restart duties if they are found to be inactive.  Gunicorn is monitored via PID file and /ping on port 80 - /ping located in api.py, which returns string: 'status: ok'  
  
Monit config files are stored in project dir: container2/monit/  
Gunicorn restart script is stored in project dir: container2/dash_app/start_api.sh  
  
**Command line access to watchdogs:**  
It is also possible to access and control watchdog states and status via the command line using: 
```bash
docker exec CONTAINER-NAME COMMAND ARGS
```
Available monit commands:
```bash
monit start all             			# Start all services  
monit start <name>          			# Only start the named service  
monit stop all              			# Stop all services  
monit stop <name>           			# Stop the named service  
monit restart all           			# Stop and start all services  
monit restart <name>        			# Only restart the named service  
monit monitor all           			# Enable monitoring of all services  
monit monitor <name>        			# Only enable monitoring of the named service  
monit unmonitor all         			# Disable monitoring of all services  
monit unmonitor <name>      			# Only disable monitoring of the named service  
monit reload                			# Reinitialize monit  
monit status [name]         			# Print full status information for service(s)  
monit summary [name]        			# Print short status information for service(s)  
monit report [up|down|..]   			# Report state of services. See manual for options  
monit quit                  			# Kill the monit daemon process  
monit validate              			# Check all services and start if not running  
monit procmatch <pattern>   			# Test process matching pattern  
```


**Command line access to fail2ban (container1):**
The following commands can be used with the fail2ban-client tool to manage Fail2ban:  
```bash
fail2ban-client start                           # Start Fail2ban service
fail2ban-client stop                            # Stop Fail2ban service
fail2ban-client reload                          # Reload Fail2ban configuration
fail2ban-client status                          # Show Fail2ban status and enabled jails
fail2ban-client status <jail>                   # Show status of a specific jail
fail2ban-client status <filter>                 # Show status of jails matching a filter
fail2ban-client status <service>                # Show status of jails for a specific service
fail2ban-client set <jail> enabled              # Enable a specific jail
fail2ban-client set <jail> disabled             # Disable a specific jail
fail2ban-client set <jail> banip <IP>           # Manually ban an IP address in a jail
fail2ban-client set <jail> unbanip <IP>         # Unban an IP address from a jail
fail2ban-client set <jail> banip <IP> [time]    # Ban an IP address in a jail for a specific duration
fail2ban-client set <jail> unbanip <IP> [time]  # Unban an IP address from a jail for a specific duration
fail2ban-client add <jail> <filter>             # Add a filter to a jail
fail2ban-client remove <jail> <filter>          # Remove a filter from a jail
fail2ban-client ping                            # Check if Fail2ban is running
fail2ban-client version                         # Show Fail2ban version information
fail2ban-client status [service]                # Show full status information for all or a specific service
fail2ban-client status [<jail>...]              # Show status information for one or multiple jails
fail2ban-client get <jail> logpath              # Get the log path for a specific jail
fail2ban-client get <jail> loglevel             # Get the log level for a specific jail
fail2ban-client get <jail> maxretry             # Get the maximum number of retries for a specific jail
```

**How to send commands to containers:**
To interact with running containers, you can use the 'docker exec' command:  
```bash
docker exec [OPTIONS] CONTAINER COMMAND [ARG...]
```
For instance, if you have a container named my-container and you want to run the ls command inside it, the command would be:  
```bash
docker exec my-container ls
```
This would execute the ls command inside the my-container container and display the output of the ls command in your terminal.  

You can also use additional options with docker exec to modify its behavior, such as -it to allocate a pseudo-TTY and keep STDIN open.  
This can be useful when running interactive commands inside the container.  
```bash
docker exec -it container_name command
```
Using the -it option allows you to interact with the command running inside the container, as if you were working directly in a terminal session within the container.  

---

### Getting started
1. Clone the innovation-hub-api-container project repo to your local host  
2. Install Docker and Docker-Compose
3. Create the user:password file using your preferred method – see below for options.  
4. Edit the docker-compose.yml file to your preferred setting, adjust the options to fit your desired log level and location (hosted or in container only) and make sure the container1 htpasswd volume is pointing to your created user:password file  
	- or If wanting to store logs on host, make sure the log volume is pointing to the desired local directory path  
5. Start build and start process with:  
	- To run live and see outputs: ‘docker-compose up  --build --remove-orphans’  
	- To run daemonised: ‘docker-compose up  -d --build --remove-orphans’  
6. Browse to http://localhost/api/ to access the innovation hub API.  
	- Enter username and password  
	- **default user**  
		- username: admin  
		- password: admin  
7. Enjoy the API!  
  
With container images now built, to start/stop containers, use the following:  
Stop containers: 
```bash
'docker-compose down'
```
  
Start containers:  
```bash
'docker-compose up'
```
  
OPTIONAL  
8.  Browse to http://localhost/monit/ to access container1 watchdog status web portal
  - Enter username and password
  - **default user**  
    - username: admin  
    - password: admin

---

### User Authentication
NGINX basic authentication user access is managed through a txt file container user:password combinations for referencing requests against.  This file needs to be passed/shared with container1.  And while it is possible to simply pass such a file in plain text, it is much safer to first encrypt the passwords listed before doing so…  
  
The simplest way to make such an encrypted user:password file is to use the apache2-utils library on Linux – the following is for Debian systems but can be modified for others.  
  
To get the library installed run:  
```bash
‘apt-get update && apt-get install apache2-utils -y’
```
Then run as root, run:  
```bash
‘htpasswd -c .htpasswd username’
```
This will start the application, create the file, then ask you to input the password.  
  
To add more users, simply rerun the command, but use the -b flag in place of the -c flag.  
  
Or, if you have many users you wish to add, I have included a small BASH script (password_script.sh) that can automate the process by reading a plain text user:password structured file and converting it to an encrypted password version for you.  
  
This script is located within the /scripts directory within the main project directory.  
  
to use, create a text file with a user:password text pair per user, per line (see example file user_credentials.txt, also located in /scripts).  
Then call script with the text file as the first argument. e.g.:  
```bash
‘ ./password_script user_credentials.txt’
```
  
e.g., user_credentials.txt file layout for creating 3 users:  
```bash
user1:password1
user2:password2
user3:password3
```

---
