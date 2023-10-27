# Gunicorn configuration file.

# innovation-hub-api - container2 - api/gunicorn_config.py
# written by: Andrew McDonald
# initial: 23/05/23
# current: 17/07/23
# version: 0.9

from email.mime import application
from multiprocessing import cpu_count
from os import environ
from api import app

def max_workers():
    return cpu_count()

environ.get('APP_PORT', '8050')
bind = '0.0.0.0:' + environ.get('APP_PORT', '8050')

#threads_default = max_workers() - 1
threads_default = 1
worker_tmp_dir = '/dev/shm'
workers = 1 #environ.get('APP_WORKERS', max_workers())
threads = 1 #environ.get('APP_THREADS', threads_default)

timeout = 60  # Set the worker timeout to 60 seconds (adjust as needed)

spew = False

pidfile = '/var/run/gunicorn.pid'

# set log locations
#gunicorn_log = '/home/innovation-hub-api/persistent/logs/container2/gunicorn.log'
gunicorn_log = '/home/innovation-hub-api/persistent/logs/container2/gunicorn.log'
gunicorn_access_log = '/home/innovation-hub-api/persistent/logs/container2/gunicorn-access.log'

accesslog = gunicorn_access_log
errorlog = gunicorn_log
loglevel = environ.get('APP_LOG_LEVEL', 'info').lower()

proc_name = 'app'

# Use the 'app' variable as the WSGI application
application = app

# Set the worker class to gevent for async operations
worker_class = 'gevent'

# Set the worker connections to 500 for concurrency limit
worker_connections = 500

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    pass

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

    ## get traceback info
    import threading, sys, traceback
    id2name = {th.ident: th.name for th in threading.enumerate()}
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(threadId,""),
            threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename,
                lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    worker.log.debug("\n".join(code))

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")
