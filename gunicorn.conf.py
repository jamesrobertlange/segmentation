workers = 2
worker_class = 'sync'  # Change this from 'aiohttp.worker.GunicornWebWorker' to 'sync'
timeout = 300  # 5 minutes
max_requests = 1000
max_requests_jitter = 50