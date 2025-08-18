#!/bin/bash

# Database Dependencies Installation Script for ML Engine (macOS Only)
# This script installs system dependencies required for:
# - psycopg (PostgreSQL)
# - cx-oracle (Oracle)
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

# Install Oracle Instant Client manually (Homebrew formula doesn't exist)
echo "🐘 Installing Oracle Instant Client manually..."
ORACLE_VERSION="21.12"
ORACLE_DIR="$HOME/oracle"
mkdir -p $ORACLE_DIR

# Download and install Oracle Instant Client Basic
echo "📥 Downloading Oracle Instant Client Basic..."
curl -L -o /tmp/oracle-basic.zip "https://download.oracle.com/otn_software/mac/instantclient/2112000/instantclient-basic-macos.x64-21.12.0.0.0.zip"
unzip -q /tmp/oracle-basic.zip -d $ORACLE_DIR

# Download and install Oracle Instant Client SDK
echo "📥 Downloading Oracle Instant Client SDK..."
curl -L -o /tmp/oracle-sdk.zip "https://download.oracle.com/otn_software/mac/instantclient/2112000/instantclient-sdk-macos.x64-21.12.0.0.0.zip"
unzip -q /tmp/oracle-sdk.zip -d $ORACLE_DIR

# Create symlink for easier access
ln -sf $ORACLE_DIR/instantclient_21_12 $ORACLE_DIR/instantclient

# Set up Oracle environment
echo "🐘 Setting up Oracle Instant Client environment..."
ORACLE_HOME="$ORACLE_DIR/instantclient"
echo "export ORACLE_HOME=$ORACLE_HOME" >> ~/.zshrc
echo "export DYLD_LIBRARY_PATH=$ORACLE_HOME:\$DYLD_LIBRARY_PATH" >> ~/.zshrc
echo "export PATH=$ORACLE_HOME:\$PATH" >> ~/.zshrc

# Also add to bash profile if it exists
if [ -f ~/.bash_profile ]; then
    echo "export ORACLE_HOME=$ORACLE_HOME" >> ~/.bash_profile
    echo "export DYLD_LIBRARY_PATH=$ORACLE_HOME:\$DYLD_LIBRARY_PATH" >> ~/.bash_profile
    echo "export PATH=$ORACLE_HOME:\$PATH" >> ~/.bash_profile
fi

# Clean up
rm -f /tmp/oracle-basic.zip /tmp/oracle-sdk.zip

echo "✅ Oracle environment variables added to shell profiles."
echo "   Please restart your terminal or run 'source ~/.zshrc' to apply changes."

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
echo "   • Oracle Instant Client (for cx-oracle)"
echo "   • Microsoft ODBC Driver for SQL Server (for MSSQL connections)"
echo ""
echo "🔧 Next steps:"
echo "   1. Restart your terminal to ensure environment variables are loaded"
echo "   2. Run 'poetry install' to install Python packages"
echo "   3. Test your database connections"
echo ""
echo "💡 Note: You may need to install specific ODBC drivers for your databases:"
echo "   • SQL Server: Microsoft ODBC Driver for SQL Server ✅"
echo "   • PostgreSQL: psqlODBC"
echo "   • MySQL: MySQL ODBC Driver"
echo "   • Oracle: Oracle ODBC Driver"
echo ""
echo "🌐 For more information, visit:"
echo "   • psycopg: https://www.psycopg.org/docs/install.html"
echo "   • cx-oracle: https://cx-oracle.readthedocs.io/en/latest/user_guide/installation.html"
echo "   • pymysql: https://pymysql.readthedocs.io/en/latest/user/installation.html"
echo "   • pyodbc: https://github.com/mkleehammer/pyodbc/wiki/Install"
