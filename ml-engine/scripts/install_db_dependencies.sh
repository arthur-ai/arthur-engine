#!/bin/bash

# Database Dependencies Installation Script for ML Engine
# This script installs system dependencies required for:
# - psycopg (PostgreSQL)
# - pymysql (MySQL)
# - pyodbc (ODBC)
# - MSSQL connections
# - Databricks connections (via ODBC)

set -e  # Exit on any error

echo "🚀 Installing database driver dependencies for ML Engine..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo "❌ Unsupported OS: $OSTYPE"
    echo "   This script supports macOS and Linux only."
    exit 1
fi

echo "📍 Detected OS: $OS"

if [[ "$OS" == "macos" ]]; then
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew is not installed. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi

    # Update Homebrew
    echo "🍎 Updating Homebrew..."
    brew update

    # Install base dependencies
    echo "📦 Installing base dependencies..."
    brew install \
        postgresql \
        mysql-connector-c \
        unixodbc

    # Install MSSQL ODBC driver for macOS
    echo "🗄️ Installing Microsoft ODBC Driver for SQL Server..."
    brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
    brew update
    brew install msodbcsql18 mssql-tools18

    echo "✅ Microsoft ODBC Driver for SQL Server installed successfully."

elif [[ "$OS" == "linux" ]]; then
    # Check for package manager
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt-get"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
    else
        echo "❌ No supported package manager found (apt-get or yum)"
        exit 1
    fi

    echo "📦 Installing base dependencies using $PKG_MANAGER..."

    if [[ "$PKG_MANAGER" == "apt-get" ]]; then
        sudo apt-get update
        sudo apt-get install -y \
            postgresql-client \
            libpq-dev \
            libmysqlclient-dev \
            unixodbc \
            unixodbc-dev
    else
        sudo yum install -y \
            postgresql-devel \
            mysql-devel \
            unixODBC \
            unixODBC-devel
    fi

    echo "✅ Base ODBC drivers installed successfully."
    echo ""
    echo "⚠️  Optional: Microsoft ODBC Driver for SQL Server (manual installation required)"
    echo "   Follow instructions at: https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server"
fi

# Common warnings
echo ""
echo "⚠️  Oracle Instant Client requires manual download due to license restrictions."
echo "   It is not installed by this script. Please refer to the README for installation instructions."
echo ""
echo "⚠️  Databricks ODBC Driver (Simba Spark ODBC Driver) requires manual installation."
echo "   Download from: https://www.databricks.com/spark/odbc-drivers-download"
echo "   Note: The Databricks connector defaults to SQL connector method which doesn't require ODBC."

echo ""
echo "✅ Database dependencies installation completed!"
echo ""
echo "📋 Summary of installed components:"
echo "   • PostgreSQL client libraries (for psycopg)"
echo "   • MySQL client libraries (for pymysql)"
echo "   • ODBC driver manager (unixODBC - for pyodbc)"
if [[ "$OS" == "macos" ]]; then
    echo "   • Microsoft ODBC Driver for SQL Server (for MSSQL connections)"
fi
echo ""
echo "🔧 Next steps:"
echo "   • Restart your terminal to ensure environment variables are loaded"
echo "   • Install Databricks ODBC driver if using Databricks ODBC connection method"
echo "   • Run 'poetry install' to install Python dependencies"
echo ""
echo "🌐 For more information, visit:"
echo "   • psycopg: https://www.psycopg.org/docs/install.html"
echo "   • pymysql: https://pymysql.readthedocs.io/en/latest/user/installation.html"
echo "   • pyodbc: https://github.com/mkleehammer/pyodbc/wiki/Install"
echo "   • Databricks ODBC: https://www.databricks.com/spark/odbc-drivers-download"
