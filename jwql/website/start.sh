#!/bin/bash
exec gunicorn jwql.website.jwql_proj.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3