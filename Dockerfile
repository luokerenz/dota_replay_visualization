FROM python:alpine

MAINTAINER DDD

RUN pip install flask pandas mysql-python
RUN git clone https://github.com/luokerenz/dota_replay_visualization /home/flask

EXPOSE 5000

ENTRYPOINT ["python", "/home/flask/app.py"]
