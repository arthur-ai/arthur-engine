#!/bin/bash

# Database Dependencies Installation Script for ML Engine
# This script installs system dependencies required for:
# - psycopg (PostgreSQL)
# - cx-oracle (Oracle)
# - pymysql (MySQL)
# - pyodbc (ODBC)

set -e  # Exit on any error

# Function to install Oracle Instant Client
install_oracle_client() {
    echo "🐘 Installing Oracle Instant Client..."
    ORACLE_VERSION="21.12"
    ORACLE_DIR="/opt/oracle"
    sudo mkdir -p $ORACLE_DIR

    # Download and install Oracle Instant Client Basic
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-basic-linux.x64-21.12.0.0.0.zip -O /tmp/oracle-basic.zip
    sudo unzip -q /tmp/oracle-basic.zip -d $ORACLE_DIR
    sudo ln -sf $ORACLE_DIR/instantclient_21_12 $ORACLE_DIR/instantclient

    # Download and install Oracle Instant Client SDK
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-sdk-linux.x64-21.12.0.0.0.zip -O /tmp/oracle-sdk.zip
    sudo unzip -q /tmp/oracle-sdk.zip -d $ORACLE_DIR

    # Set environment variables
    echo "export ORACLE_HOME=$ORACLE_DIR/instantclient" | sudo tee -a /etc/environment
    echo "export LD_LIBRARY_PATH=$ORACLE_DIR/instantclient:\$LD_LIBRARY_PATH" | sudo tee -a /etc/environment
    echo "export PATH=$ORACLE_DIR/instantclient:\$PATH" | sudo tee -a /etc/environment

    # Clean up
    rm -f /tmp/oracle-basic.zip /tmp/oracle-sdk.zip
}

echo "🚀 Installing database driver dependencies for ML Engine..."

# Detect operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        echo "📦 Detected Debian/Ubuntu system, using apt-get..."
        sudo apt-get update
        sudo apt-get install -y \
            libpq-dev \
            postgresql-client \
            unixodbc \
            unixodbc-dev \
            libmysqlclient-dev \
            default-libmysqlclient-dev \
            build-essential \
            python3-dev \
            libaio-dev \
            wget

        # Install Oracle Instant Client
        install_oracle_client

    elif command -v yum &> /dev/null; then
        echo "📦 Detected RHEL/CentOS/Fedora system, using yum..."
        sudo yum update -y
        sudo yum install -y \
            postgresql-devel \
            postgresql \
            unixODBC \
            unixODBC-devel \
            mysql-devel \
            gcc \
            gcc-c++ \
            python3-devel \
            libaio-devel \
            wget

        # Install Oracle Instant Client
        install_oracle_client

    else
        echo "❌ Unsupported Linux distribution. Please install dependencies manually."
        exit 1
    fi

elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "🍎 Detected macOS system, using Homebrew..."

    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew is not installed. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi

    # Update Homebrew
    brew update

    # Install dependencies
    brew install \
        postgresql \
        mysql-connector-c \
        unixodbc \
        oracle-instantclient \
        libaio

    # Set up Oracle environment
    echo "🐘 Setting up Oracle Instant Client environment..."
    ORACLE_HOME=$(brew --prefix oracle-instantclient)
    echo "export ORACLE_HOME=$ORACLE_HOME" >> ~/.zshrc
    echo "export DYLD_LIBRARY_PATH=$ORACLE_HOME/lib:\$DYLD_LIBRARY_PATH" >> ~/.zshrc
    echo "export PATH=$ORACLE_HOME/bin:\$PATH" >> ~/.zshrc

    # Also add to bash profile if it exists
    if [ -f ~/.bash_profile ]; then
        echo "export ORACLE_HOME=$ORACLE_HOME" >> ~/.bash_profile
        echo "export DYLD_LIBRARY_PATH=$ORACLE_HOME/lib:\$DYLD_LIBRARY_PATH" >> ~/.bash_profile
        echo "export PATH=$ORACLE_HOME/bin:\$PATH" >> ~/.bash_profile
    fi

    echo "✅ Oracle environment variables added to shell profiles."
    echo "   Please restart your terminal or run 'source ~/.zshrc' to apply changes."

else
    echo "❌ Unsupported operating system: $OSTYPE"
    echo "   Please install dependencies manually for your system."
    exit 1
fi

echo ""
echo "✅ Database dependencies installation completed!"
echo ""
echo "📋 Summary of installed components:"
echo "   • PostgreSQL client libraries (for psycopg)"
echo "   • MySQL client libraries (for pymysql)"
echo "   • ODBC driver manager (for pyodbc)"
echo "   • Oracle Instant Client (for cx-oracle)"
echo ""
echo "🔧 Next steps:"
echo "   1. Restart your terminal to ensure environment variables are loaded"
echo "   2. Run 'poetry install' to install Python packages"
echo "   3. Test your database connections"
echo ""
echo "💡 Note: You may need to install specific ODBC drivers for your databases:"
echo "   • SQL Server: Microsoft ODBC Driver for SQL Server"
echo "   • PostgreSQL: psqlODBC"
echo "   • MySQL: MySQL ODBC Driver"
echo "   • Oracle: Oracle ODBC Driver"
echo ""
echo "🌐 For more information, visit:"
echo "   • psycopg: https://www.psycopg.org/docs/install.html"
echo "   • cx-oracle: https://cx-oracle.readthedocs.io/en/latest/user_guide/installation.html"
echo "   • pymysql: https://pymysql.readthedocs.io/en/latest/user/installation.html"
echo "   • pyodbc: https://github.com/mkleehammer/pyodbc/wiki/Install"
