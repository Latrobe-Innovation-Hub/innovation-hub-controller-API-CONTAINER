# innovation-hub-api - container2 - api/api_config.py
# written by: Andrew McDonald
# initial: 23/05/23
# current: 17/07/23
# version: 0.9

import os
import logging

# set log level from user input - default INFO if non given
app_log_level = os.environ.get('APP_LOG_LEVEL', 'INFO').upper()

if app_log_level == 'DEBUG':
    APP_LOG_LEVEL = 'DEBUG'
elif app_log_level == 'INFO':
    APP_LOG_LEVEL = 'INFO'
elif app_log_level == 'WARNING':
    APP_LOG_LEVEL = 'WARNING'
elif app_log_level == 'ERROR':
    APP_LOG_LEVEL = 'ERROR'
elif app_log_level == 'CRITICAL':
    APP_LOG_LEVEL = 'CRITICAL'
else:
    APP_LOG_LEVEL = 'INFO'

## =================
## Configure Logging
## =================

logger = logging.getLogger()

# get/set Dash app port from user input - default 8050 if none given
APP_PORT = os.environ.get('API_PORT', 8050)

# get sql verbosity from user input
sql_logging = os.environ.get('SQL_VERBOSE', 'NO').upper()

if sql_logging == 'YES':
    SQL_VERBOSE = True
else:
    SQL_VERBOSE = False

logger.debug(f'SQL_LOGGING: {SQL_VERBOSE}')

