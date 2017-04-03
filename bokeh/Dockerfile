FROM python:2.7-alpine
MAINTAINER DDD

RUN apk add --no-cache g++ && \
    ln -s /usr/include/locale.h /usr/include/xlocale.h && \
    pip install cython==0.25.2 numpy==1.12.0 && \
    pip install pandas==0.19.2

RUN pip install flask pymongo bokeh

COPY . /home/

EXPOSE 5006

ENTRYPOINT ["bokeh","serve","/home/bokeh/main.py", "--port", "5006", "--host", "127.0.0.1:5006"]
