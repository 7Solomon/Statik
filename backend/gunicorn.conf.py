import multiprocessing
import sys

bind = "0.0.0.0:8000"
workers = 2
threads = 2
worker_class = "gthread"
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
preload_app = True
capture_output = True
enable_stdio_inheritance = True

def on_starting(server):
    print("--- GUNICORN STARTING ---")
    sys.stdout.flush()

def post_worker_init(worker):
    print(f"--- WORKER {worker.pid} STARTED ---")
    sys.stdout.flush()