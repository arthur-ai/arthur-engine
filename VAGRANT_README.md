# Arthur Engine - Vagrant Development Environment

This Vagrantfile sets up a Linux VM for developing Arthur Engine with all necessary dependencies and port mappings.

## Prerequisites

- [Vagrant](https://www.vagrantup.com/downloads) installed
- [VirtualBox](https://www.virtualbox.org/wiki/Downloads) installed
- At least 4GB RAM available for the VM

## Quick Start

1. **Start the VM:**

   ```bash
   vagrant up
   ```

2. **SSH into the VM:**

   ```bash
   vagrant ssh
   ```

3. **Start the GenAI Engine:**

   ```bash
   cd genai-engine
   docker-compose up
   ```

4. **Access the application:**
   - GenAI Engine UI: http://localhost:8435
   - PostgreSQL: localhost:5432

## VM Configuration

- **OS:** Ubuntu 22.04 LTS (Jammy)
- **Memory:** 4GB RAM
- **CPUs:** 2 cores
- **Hostname:** arthur-engine-dev

## Installed Software

- Docker & Docker Compose
- Node.js 20.x
- Python 3.12
- Poetry (Python package manager)
- Git, curl, wget, build tools

## Port Mappings

| Service      | Guest Port | Host Port | Description             |
| ------------ | ---------- | --------- | ----------------------- |
| GenAI Engine | 8435       | 8435      | Main application server |
| PostgreSQL   | 5432       | 5432      | Database server         |

## File Synchronization

The entire repository is mounted at `/vagrant` in the VM, so any changes you make on your host machine will be immediately available in the VM.

## Useful Commands

```bash
# Start the VM
vagrant up

# SSH into the VM
vagrant ssh

# Stop the VM
vagrant halt

# Destroy the VM (removes all data)
vagrant destroy

# Reload the VM (after changing Vagrantfile)
vagrant reload

# Check VM status
vagrant status
```

## Development Workflow

1. Make changes to your code on your host machine
2. Changes are automatically synced to the VM
3. Run `docker-compose up` in the VM to test changes
4. Access the application at http://localhost:8435 from your host browser

## Troubleshooting

### Port conflicts

If you get port conflicts, you can modify the port mappings in the Vagrantfile:

```ruby
config.vm.network "forwarded_port", guest: 8435, host: 8436  # Change host port
```

### Memory issues

If the VM runs slowly, you can increase memory in the Vagrantfile:

```ruby
vb.memory = "6144"  # Increase to 6GB
```

### Docker permission issues

If you get Docker permission errors, make sure you're in the docker group:

```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

## Notes

- The VM will automatically install all dependencies on first boot
- The repository is mounted at `/vagrant` in the VM
- All Docker containers will have access to the synced files
- The VM includes persistent volumes for PostgreSQL and Hugging Face cache
