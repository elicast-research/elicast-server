FROM python:3-stretch

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /elicast-server-wdir/
WORKDIR /elicast-server-wdir/
RUN pip install -U pip \
    && pip install -r requirements.txt

COPY server.py /elicast-server-wdir/server.py
COPY app/ /elicast-server-wdir/app/
COPY configs/ /elicast-server-wdir/configs/
