# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Use Ubuntu 22.04 LTS as the base box
  config.vm.box = "ubuntu/jammy64"
  
  # Configure the VM
  config.vm.hostname = "arthur-engine-dev"
  
  # Allocate more resources for development
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "8192"
    vb.cpus = 2
    vb.name = "arthur-engine-dev"
  end
  
  # Port forwarding for GenAI Engine services
  # Main GenAI Engine server
  config.vm.network "forwarded_port", guest: 8435, host: 8435, id: "genai-engine"
  config.vm.network "forwarded_port", guest: 3030, host: 3030, id: "genai-engine"
  
  # PostgreSQL database
  config.vm.network "forwarded_port", guest: 5432, host: 5432, id: "postgres"
  
  # Optional: Adminer for database management (uncomment if needed)
  # config.vm.network "forwarded_port", guest: 8080, host: 8080, id: "adminer"
  
  # Sync the current directory to /vagrant in the VM
  config.vm.synced_folder ".", "/vagrant", type: "virtualbox"
  
  # Provision the VM with necessary dependencies
  config.vm.provision "shell", inline: <<-SHELL
    # Update package list
    apt-get update
    
    # Install essential packages
    apt-get install -y \
      curl \
      wget \
      git \
      build-essential \
      software-properties-common \
      apt-transport-https \
      ca-certificates \
      gnupg \
      lsb-release
    
    # Install Docker
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Add vagrant user to docker group
    usermod -aG docker vagrant
    
    # Install Docker Compose (standalone)
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Install Node.js (for UI development)
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    
    # Install Python 3.12 and pip
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip
    
    # Install Poetry
    curl -sSL https://install.python-poetry.org | python3 -
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> /home/vagrant/.bashrc
    
    # Create a symlink for easier access
    ln -sf /vagrant /home/vagrant/arthur-engine
    
    # Set up environment
    echo "cd /vagrant" >> /home/vagrant/.bashrc
    echo "echo 'Welcome to Arthur Engine Development Environment!'" >> /home/vagrant/.bashrc
    echo "echo 'Repository is mounted at /vagrant'" >> /home/vagrant/.bashrc
    echo "echo 'GenAI Engine will be available at http://localhost:8435'" >> /home/vagrant/.bashrc
    echo "echo 'PostgreSQL will be available at localhost:5432'" >> /home/vagrant/.bashrc
    echo "echo ''" >> /home/vagrant/.bashrc
    echo "echo 'To start the development environment:'" >> /home/vagrant/.bashrc
    echo "echo '  cd genai-engine'" >> /home/vagrant/.bashrc
    echo "echo '  docker-compose up'" >> /home/vagrant/.bashrc
    echo "echo ''" >> /home/vagrant/.bashrc
    
    # Clean up
    apt-get autoremove -y
    apt-get clean
  SHELL
  
  # Configure the VM to use the synced folder as the working directory
  config.vm.provision "shell", inline: <<-SHELL
    # Make sure the vagrant user owns the synced folder
    chown -R vagrant:vagrant /vagrant
  SHELL
end
