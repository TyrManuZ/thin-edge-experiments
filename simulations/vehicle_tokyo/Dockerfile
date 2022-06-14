FROM python:alpine

RUN pip install paho-mqtt

COPY positions.csv /positions.csv
COPY vehicle_sim.py /vehicle_sim.py

CMD [ "python", "./vehicle_sim.py" ]