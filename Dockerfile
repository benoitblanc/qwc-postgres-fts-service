FROM sourcepole/qwc-uwsgi-base:alpine-v2023.10.26

ADD . /srv/qwc_service

RUN \
    apk add --no-cache --update --virtual runtime-deps postgresql-libs && \
    apk add --no-cache --update --virtual build-deps git postgresql-dev g++ python3-dev && \
    pip3 install --no-cache-dir -r /srv/qwc_service/requirements/requirements.txt && \
    apk del build-deps

ENV SERVICE_MOUNTPOINT=/api/v1/postgresfts
