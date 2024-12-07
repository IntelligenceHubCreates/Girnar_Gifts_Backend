FROM python:3.10.0
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
COPY app /app/

COPY app_entrypoint.sh /app
COPY wait-for-it.sh /app

CMD [ "./app_entrypoint.sh" ]