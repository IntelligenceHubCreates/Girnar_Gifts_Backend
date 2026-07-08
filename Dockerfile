FROM python:3.10.0
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# FIX: previously `COPY app /app/` flattened the `app` package directly into
# WORKDIR /app (so /app/main.py instead of /app/app/main.py), breaking every
# `from app.X import ...` / `app.main:server` import outside of local dev -
# it only ever "worked" because compose.girnar-local.yml bind-mounts the
# whole repo over /app at runtime, silently masking the bug. Same gap for
# alembic.ini/alembic/, which the entrypoint's `alembic upgrade head` needs
# and which were never copied into the image at all. Preserve real structure:
COPY app /app/app/
COPY alembic /app/alembic/
COPY alembic.ini /app/alembic.ini

COPY app_entrypoint.sh /usr/local/bin/
COPY wait-for-it.sh /usr/local/bin/

RUN sed -i 's/\r$//' /usr/local/bin/app_entrypoint.sh && chmod +x /usr/local/bin/app_entrypoint.sh && \
    sed -i 's/\r$//' /usr/local/bin/wait-for-it.sh && chmod +x /usr/local/bin/wait-for-it.sh && \
    sed -i 's|./wait-for-it.sh|wait-for-it.sh|g' /usr/local/bin/app_entrypoint.sh

CMD [ "app_entrypoint.sh" ]