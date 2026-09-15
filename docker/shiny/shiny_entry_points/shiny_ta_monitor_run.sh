#!/bin/sh

until cd /shiny_apps
do
    echo "Waiting for server volume..."
done

shiny run app_ta_monitor.py --host 0.0.0.0 --port 8000 --log-level info

tail -f /dev/null
