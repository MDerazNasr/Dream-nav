FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/opt/dreamnav

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        colmap \
        ffmpeg \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dreamnav

COPY services/api/app /opt/dreamnav/app
COPY services/remote_dense/remote_dense_app/colmap_command_adapter.py /opt/dreamnav/remote_dense_app/colmap_command_adapter.py

ENTRYPOINT ["python3", "/opt/dreamnav/remote_dense_app/colmap_command_adapter.py"]
