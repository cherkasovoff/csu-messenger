#!/bin/bash

runWorker () {
  venv/bin/python -m celery -A worker worker --logfile=/dev/null & echo "$!"
}

runScheduler () {
  venv/bin/python -m celery -A worker beat --logfile=/dev/null & echo "$!"
}

runWorker & runScheduler