#!/usr/bin/env python3
"""
RQ Worker configuration with custom timeout settings
"""
import os
import sys
from rq import Worker, Connection
import redis

def main():
    redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    
    # Connect to Redis
    redis_conn = redis.from_url(redis_url)
    
    # Create worker with custom job timeout (5 minutes)
    worker = Worker(['default'], connection=redis_conn, job_timeout=300)
    
    print(f"Starting RQ worker with job timeout: 300 seconds")
    print(f"Redis URL: {redis_url}")
    
    # Start the worker
    worker.work()

if __name__ == '__main__':
    main()
