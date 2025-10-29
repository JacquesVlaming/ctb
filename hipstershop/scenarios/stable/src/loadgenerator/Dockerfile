FROM python:3.8

COPY requirements.txt .

RUN pip install -r requirements.txt
RUN pip install python-dateutil

COPY . .
RUN chmod +x ./loadgen.sh
ENTRYPOINT ./loadgen.sh
