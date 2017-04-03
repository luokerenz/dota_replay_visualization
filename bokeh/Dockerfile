FROM python:2.7-alpine
MAINTAINER DDD

RUN apk add --no-cache g++ && \
    ln -s /usr/include/locale.h /usr/include/xlocale.h && \
    pip install cython==0.25.2 numpy==1.12.0 && \
    pip install pandas==0.19.2

RUN pip install flask pymongo bokeh

COPY . /home/bokeh/

EXPOSE 5006

ENTRYPOINT ["bokeh","serve","/home/bokeh/replay.py", "--port", "5006", "--host", "dota.luokerenz.com:5006", "--allow-websocket-origin=dota.luokerenz.com"]
