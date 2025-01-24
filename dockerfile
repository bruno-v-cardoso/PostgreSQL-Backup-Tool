FROM python:3.13.1-alpine3.21
RUN apk --no-cache add postgresql15-client

COPY requirements.txt /.
RUN pip install -r /requirements.txt

COPY full_backup_postgresql.py /.

RUN mkdir -p BACKUPS_POSTGRES

ENV POSTGRESQL__SERVER=postgres
ENV POSTGRESQL__USER={USER} # replace {USER} with your postgres user
ENV POSTGRESQL__PASSWORD={PASSWORD} # replace {PASSWORD} with your postgres password
ENV RETAIN__BACKUP__IN__DAYS=5
ENV BACKUP__FOLDER=/BACKUPS_POSTGRES
ENV PROMETHEUS__PUSHGATEWAY__SERVER=prometheus_pushgateway:9091

ENTRYPOINT ["python", "-u", "full_backup_postgresql.py"]