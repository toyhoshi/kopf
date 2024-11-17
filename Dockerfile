FROM python:3.8-slim

RUN pip install kopf kubernetes

COPY logchecker_operator.py /logchecker_operator.py

ENTRYPOINT ["kopf", "run", "/logchecker_operator.py"]

