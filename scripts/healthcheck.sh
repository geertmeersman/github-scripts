#!/bin/bash

# Check if Flask web interface is up
WEB_PORT="${WEB_PORT:-80}"
if ! curl -sf http://localhost:$WEB_PORT >/dev/null; then
  echo "Flask not responding on port $WEB_PORT"
  exit 1
fi

exit 0
