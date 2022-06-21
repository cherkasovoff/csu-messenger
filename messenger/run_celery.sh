#!/bin/bash

runWorker () {
  venv/bin/python -m celery -A worker worker & echo "$!"
}

runScheduler () {
  venv/bin/python -m celery -A worker beat & echo "$!"
}

runWorker & runScheduler