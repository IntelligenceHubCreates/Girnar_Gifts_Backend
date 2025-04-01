#!/bin/bash

# Wait for the database to be ready
./wait-for-it.sh db:5432 --timeout=30 --strict -- echo "Database is up"

# Run Alembic migrations
alembic upgrade head

export PGPASSWORD=silveesilver

# Check if the record exists in the database
RECORD_CHECK_QUERY="SELECT * FROM users WHERE id = 1;"
RECORD_INSERT_QUERY="INSERT INTO users (email, confirmed, hashed_password, role) VALUES ('qualityagency79@gmail.com', true, '\$2b\$12\$cJBilV25TGMT31YgLXAk7e1.r9RHrm/UXLFqjzYuiD1E.blSecbuq', 1);"  #mynewbackendtestedis

# Use psql to connect to PostgreSQL and check for the record
RECORD_EXISTS=$(psql -h db -U silvee -d silverdatabase -t -c "$RECORD_CHECK_QUERY")

# If the record doesn't exist, insert it
# echo "Inserting initial record into the database..."
# psql -h db -U postgres -d app -c "$RECORD_INSERT_QUERY"
if [ -z "$RECORD_EXISTS" ]; then
    echo "Inserting initial record into the database..."
    psql -h db -U silvee -d silverdatabase -c "$RECORD_INSERT_QUERY"
else
    echo "Record already exists, skipping insert."
fi



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
  uvicorn app.main:server --host=0.0.0.0 --reload
fi