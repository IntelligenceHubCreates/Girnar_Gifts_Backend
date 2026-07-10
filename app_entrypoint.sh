#!/bin/bash

# Wait for the database to be ready
# Use env vars passed from docker-compose
./wait-for-it.sh $POSTGRES_SERVER:$POSTGRES_PORT --timeout=30 --strict -- echo "Database port is open"

# Additional check: Wait for PostgreSQL to be ready to accept connections
echo "Waiting for PostgreSQL to be ready..."
export PGPASSWORD=$POSTGRES_PASSWORD
until psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -c '\q' 2>/dev/null; do
  echo "PostgreSQL is still starting up... waiting"
  sleep 1
done
echo "PostgreSQL is ready!"

# Run Alembic migrations
alembic upgrade head

# Admin accounts are provisioned via app/scripts/seed_admin.py (reads
# SEED_ADMIN_PASSWORD from env), not auto-inserted here.

if [ "$DEBUG" = "debugpy" ]
then
  echo "Running in debug mode"
  pip install debugpy -t /tmp
  python /tmp/debugpy --listen 0.0.0.0:6789 -m uvicorn app.main:server --host 0.0.0.0 --port 8000 --reload
elif [ "$DEBUG" = "pdb" ]
then
  echo "Running with PDB"
  pip install web-pdb
  uvicorn app.main:server --host=0.0.0.0 --reload
else
  echo "Running in production mode"
  # Binds to $PORT when the platform assigns one dynamically; local
  # docker-compose doesn't set PORT, so this still defaults to 8000
  # (matching compose.girnar-local.yml's 8010->8000 mapping) unchanged.
  uvicorn app.main:server --host=0.0.0.0 --port="${PORT:-8000}" --reload
fi