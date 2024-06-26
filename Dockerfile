FROM sourcepole/qwc-uwsgi-base:alpine-v2023.10.26

ADD requirements/requirements.txt /srv/qwc_service/requirements.txt

RUN \
    apk add --no-cache --update --virtual runtime-deps postgresql-libs && \
    apk add --no-cache --update --virtual build-deps git postgresql-dev g++ python3-dev && \
    pip3 install --no-cache-dir -r /srv/qwc_service/requirements.txt && \
    apk del build-deps

ADD src /srv/qwc_service/

ENV SERVICE_MOUNTPOINT=/api/v1/postgresfts
