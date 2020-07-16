FROM python:3.7.2-slim

MAINTAINER sergey Leonov 'lss.umnic@gmail.com'

COPY ./python_app /opt/app

WORKDIR /opt/app
RUN apt-get update && apt-get install -y netcat
RUN pip --no-cache-dir install -r requirements.txt

EXPOSE 5000

ENV PYTHONUNBUFFERED 1

ENV MYSQL_DATABASE_HOST localhost
ENV MYSQL_DATABASE_DB mytestdatabase
ENV MYSQL_DATABASE_USER root
ENV MYSQL_DATABASE_PASSWORD password

RUN useradd user
RUN chown -R user:user /opt/app
USER user

ENTRYPOINT ["/bin/sh", "app-start.sh"]

