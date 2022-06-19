from os import getenv

from redis import asyncio as aioredis


redis = aioredis.from_url(f"redis://lanhost:{getenv('REDIS_PORT', 6379)}")
