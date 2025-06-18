# Use official slim Python 3.11 base image
FROM python:3.11-slim

# Install required system packages:
RUN apt-get update && \
    apt-get install -y cron tzdata vim-tiny curl && \
    pip install requests cron-descriptor gunicorn flask flask-socketio eventlet && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Python scripts into container
COPY scripts/github/* /home/scripts/
RUN chmod +x /home/scripts/*.py

COPY scripts/container/describe_cron.py /home/cron/describe_cron.py
COPY scripts/container/cron_wrapper.py /home/cron/cron_wrapper.py
COPY scripts/flask/web_interface.py /home/web_interface.py

# Copy entrypoint and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set timezone (default: Europe/Brussels)
ENV TZ=Europe/Brussels
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Setup cron job:
# - Copy cron job config
# - Set correct permissions
COPY cron/cronjob /etc/cron.d/github_scripts
RUN chmod 0644 /etc/cron.d/github_scripts
RUN crontab /etc/cron.d/github_scripts  # Register cron job

# Copy VERSION
COPY VERSION /VERSION

# Healthcheck
COPY scripts/container/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

HEALTHCHECK CMD /healthcheck.sh

# Use custom entrypoint to start CUPS and cron
ENTRYPOINT ["/entrypoint.sh"]
