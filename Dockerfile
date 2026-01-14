FROM python:3.10.0
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
COPY app /app/

COPY app_entrypoint.sh /usr/local/bin/
COPY wait-for-it.sh /usr/local/bin/

RUN sed -i 's/\r$//' /usr/local/bin/app_entrypoint.sh && chmod +x /usr/local/bin/app_entrypoint.sh && \
    sed -i 's/\r$//' /usr/local/bin/wait-for-it.sh && chmod +x /usr/local/bin/wait-for-it.sh && \
    sed -i 's|./wait-for-it.sh|wait-for-it.sh|g' /usr/local/bin/app_entrypoint.sh

CMD [ "app_entrypoint.sh" ]