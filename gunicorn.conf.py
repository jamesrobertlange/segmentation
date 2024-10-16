workers = 2
worker_class = 'sync'
timeout = 300  # 5 minutes
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 30  # Give workers 30 seconds to finish their current request before forcefully restarting