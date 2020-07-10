FROM python:3.8-alpine

MAINTAINER sergey Leonov 'lss.umnic@gmail.com'

COPY ./python_app /opt/app

WORKDIR /opt/app

RUN pip --no-cache-dir install -r requirements.txt

EXPOSE 5000

ENV PYTHONUNBUFFERED 1

ENV MYSQL_DATABASE_HOST localhost
ENV MYSQL_DATABASE_DB mytestdatabase
ENV MYSQL_DATABASE_USER root
ENV MYSQL_DATABASE_PASSWORD password

RUN adduser -D user
RUN chown -hR user:user /opt/app
USER user

ENTRYPOINT ["/bin/sh", "app-start.sh"]

