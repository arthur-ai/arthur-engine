#!/bin/bash

# Database Dependencies Installation Script for ML Engine (Docker)
# This script installs system dependencies required for:
# - psycopg (PostgreSQL)
# - cx-oracle (Oracle)
# - pymysql (MySQL)
# - pyodbc (ODBC)
# Optimized for Debian/Ubuntu (Docker containers)

set -e  # Exit on any error

echo "🚀 Installing database driver dependencies for ML Engine (Docker)..."

# Install system dependencies for Debian/Ubuntu
echo "📦 Installing system dependencies..."
apt-get update
apt-get install -y \
    libpq-dev \
    postgresql-client \
    unixodbc \
    unixodbc-dev \
    libmariadb-dev \
    libmariadb-dev-compat \
    build-essential \
    python3-dev \
    libaio-dev \
    wget \
    unzip

# Install Oracle Instant Client
echo "🐘 Installing Oracle Instant Client..."
ORACLE_VERSION="21.12"
ORACLE_DIR="/opt/oracle"
mkdir -p $ORACLE_DIR

# Download and install Oracle Instant Client Basic
wget -q https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-basic-linux.x64-21.12.0.0.0.zip -O /tmp/oracle-basic.zip
unzip -q /tmp/oracle-basic.zip -d $ORACLE_DIR
ln -sf $ORACLE_DIR/instantclient_21_12 $ORACLE_DIR/instantclient

# Download and install Oracle Instant Client SDK
wget -q https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-sdk-linux.x64-21.12.0.0.0.zip -O /tmp/oracle-sdk.zip
unzip -q /tmp/oracle-sdk.zip -d $ORACLE_DIR

# Note: Environment variables are set in the Dockerfile
# ORACLE_HOME, LD_LIBRARY_PATH, and PATH are configured there

# Clean up
rm -f /tmp/oracle-basic.zip /tmp/oracle-sdk.zip
apt-get clean
rm -rf /var/lib/apt/lists/*

echo ""
echo "✅ Database dependencies installation completed for Docker!"
echo ""
echo "📋 Summary of installed components:"
echo "   • PostgreSQL client libraries (for psycopg)"
echo "   • MySQL client libraries (for pymysql)"
echo "   • ODBC driver manager (for pyodbc)"
echo "   • Oracle Instant Client (for cx-oracle)"
echo ""
echo "🔧 Next steps:"
echo "   1. Install Python packages with: poetry install"
echo "   2. Test your database connections"
