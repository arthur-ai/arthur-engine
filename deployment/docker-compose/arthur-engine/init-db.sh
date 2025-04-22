#!/bin/bash
set -e

function create_user_and_database() {
	local database=$1
	echo "  Checking if database '$database' exists"
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
	    SELECT 'CREATE DATABASE $database'
	    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
	    GRANT ALL PRIVILEGES ON DATABASE $database TO $POSTGRES_USER;
	EOSQL
}

if [ -n "$POSTGRES_DATABASES" ]; then
	echo "Multiple database creation requested: $POSTGRES_DATABASES"
	for db in $(echo "$POSTGRES_DATABASES" | tr ',' ' '); do
		create_user_and_database "$db"
	done
fi
