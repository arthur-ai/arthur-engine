#!/bin/bash

# Database Dependencies Installation Script for ML Engine (macOS Only)
# This script installs system dependencies required for:
# - psycopg (PostgreSQL)
# - pymysql (MySQL)
# - pyodbc (ODBC)
# - MSSQL connections

set -e  # Exit on any error

echo "🚀 Installing database driver dependencies for ML Engine on macOS..."

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script only supports macOS. Detected OS: $OSTYPE"
    echo "   Please use the appropriate installation method for your operating system."
    exit 1
fi

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

# Warn that Oracle Instant Client should be installed manually (Homebrew formula doesn't exist)
echo "WARNING: Oracle Instant Client requires manual download due to license restrictions."
echo "         As a result it is not installed by this script. Please refer to the README for installation instructions."

# Install MSSQL ODBC driver for macOS
echo "🗄️ Installing Microsoft ODBC Driver for SQL Server..."
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
brew install msodbcsql18 mssql-tools18

echo "✅ Microsoft ODBC Driver for SQL Server installed successfully."

echo ""
echo "✅ Database dependencies installation completed!"
echo ""
echo "📋 Summary of installed components:"
echo "   • PostgreSQL client libraries (for psycopg)"
echo "   • MySQL client libraries (for pymysql)"
echo "   • ODBC driver manager (for pyodbc)"
echo "   • Microsoft ODBC Driver for SQL Server (for MSSQL connections)"
echo ""
echo "🔧 Next steps: Restart your terminal to ensure environment variables are loaded"
echo ""
echo "🌐 For more information, visit:"
echo "   • psycopg: https://www.psycopg.org/docs/install.html"
echo "   • pymysql: https://pymysql.readthedocs.io/en/latest/user/installation.html"
echo "   • pyodbc: https://github.com/mkleehammer/pyodbc/wiki/Install"
