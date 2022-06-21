#!/bin/bash

for pid in $(ps aux | grep celery | awk {'print$2'})
do
  echo "Killing $pid"
  kill -9 "$pid"
done