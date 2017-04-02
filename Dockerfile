FROM python:2.7-alpine
MAINTAINER DDD

RUN apk add --no-cache g++ && \
    ln -s /usr/include/locale.h /usr/include/xlocale.h && \
    pip install cython==0.25.2 numpy==1.12.0 && \
    pip install pandas==0.19.2

RUN apk add --no-cache mariadb-dev mariadb-client mariadb-libs
RUN pip install flask mysql-python

COPY . /home/flask/

EXPOSE 5000

ENTRYPOINT ["python", "/home/flask/app.py"]
