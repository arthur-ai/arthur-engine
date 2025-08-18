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
echo "   Oracle Instant Client requires manual download due to license restrictions."
echo "   Please follow these steps:"
echo ""
echo "   1. Visit: https://www.oracle.com/database/technologies/instant-client/macos-intel-x86-downloads.html"
echo "   2. Accept the license agreement"
echo "   3. Download 'Basic Package' for macOS Intel x86-64"
echo "   4. Extract to: $HOME/oracle/"
echo "   5. Run this script again"
echo ""
echo "   Alternatively, you can skip Oracle for now and install other dependencies:"
echo "   - PostgreSQL, MySQL, ODBC, and MSSQL drivers will still be installed"
echo ""

# Check if Oracle is already installed
if [ -d "$HOME/oracle/instantclient" ] || [ -d "$HOME/oracle/instantclient_21_12" ] || [ -d "$HOME/oracle/instantclient_19_19" ]; then
    echo "✅ Oracle Instant Client found in $HOME/oracle/"
    ORACLE_HOME="$HOME/oracle/instantclient"

    # Find the actual instantclient directory
    if [ -d "$HOME/oracle/instantclient_21_12" ]; then
        ORACLE_HOME="$HOME/oracle/instantclient_21_12"
    elif [ -d "$HOME/oracle/instantclient_19_19" ]; then
        ORACLE_HOME="$HOME/oracle/instantclient_19_19"
    fi

    echo "   Using Oracle home: $ORACLE_HOME"
else
    echo "❌ Oracle Instant Client not found."
    echo "   Please download and install manually, then run this script again."
    echo "   Continuing with other database drivers..."
    ORACLE_HOME=""
fi



# Set up Oracle environment if Oracle is installed
if [ -n "$ORACLE_HOME" ]; then
    echo "🐘 Setting up Oracle Instant Client environment..."
    echo "export ORACLE_HOME=$ORACLE_HOME" >> ~/.zshrc
    echo "export DYLD_LIBRARY_PATH=$ORACLE_HOME:\$DYLD_LIBRARY_PATH" >> ~/.zshrc
    echo "export PATH=$ORACLE_HOME:\$PATH" >> ~/.zshrc

    # Also add to bash profile if it exists
    if [ -f ~/.bash_profile ]; then
        echo "export ORACLE_HOME=$ORACLE_HOME" >> ~/.bash_profile
        echo "export DYLD_LIBRARY_PATH=$ORACLE_HOME:\$DYLD_LIBRARY_PATH" >> ~/.bash_profile
        echo "export PATH=$ORACLE_HOME:\$PATH" >> ~/.bash_profile
    fi

    echo "✅ Oracle environment variables added to shell profiles."
    echo "   Please restart your terminal or run 'source ~/.zshrc' to apply changes."
else
    echo "⚠️  Oracle Instant Client not installed - skipping Oracle environment setup."
    echo "   You can install Oracle later and run this script again to set up environment variables."
fi

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
