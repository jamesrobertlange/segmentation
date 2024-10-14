workers = 2
worker_class = 'aiohttp.worker.GunicornWebWorker'
timeout = 300  # 5 minutes
max_requests = 1000
max_requests_jitter = 50