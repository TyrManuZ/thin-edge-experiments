FROM python:alpine

RUN pip install paho-mqtt

COPY cycle_time.py /cycle_time.py

CMD [ "python", "./cycle_time.py" ]