#!/bin/bash
# VeloSim Ansible Setup Script

set -e

echo "🚀 VeloSim Ansible Production Setup"
echo "===================================="

# Check if Ansible is installed
if ! command -v ansible &> /dev/null; then
    echo "❌ Ansible not found. Installing Ansible..."
    
    # Install Ansible based on OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt update
        sudo apt install -y software-properties-common
        sudo add-apt-repository --yes --update ppa:ansible/ansible
        sudo apt install -y ansible
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # Mac OS
        if command -v brew &> /dev/null; then
            brew install ansible
        else
            echo "❌ Homebrew not found. Please install Homebrew first or install Ansible manually."
            exit 1
        fi
    else
        echo "❌ Unsupported OS. Please install Ansible manually."
        exit 1
    fi
fi

echo "✅ Ansible found: $(ansible --version | head -1)"

# Install Ansible collections
echo "📦 Installing Ansible collections..."
ansible-galaxy collection install -r requirements.yml

# Create SSH key if not exists
SSH_KEY_PATH="$HOME/.ssh/velosim_deploy_key"
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "🔑 Generating SSH key for deployment..."
    ssh-keygen -t ed25519 -C "velosim-deploy" -f "$SSH_KEY_PATH" -N ""
    echo "✅ SSH key generated at $SSH_KEY_PATH"
    echo ""
    echo "📋 Add this public key to your GitHub account and server:"
    echo "   GitHub: https://github.com/settings/keys"
    echo "   Server: Add to ~/.ssh/authorized_keys for your user"
    echo ""
    cat "${SSH_KEY_PATH}.pub"
    echo ""
else
    echo "✅ SSH key already exists at $SSH_KEY_PATH"
fi

# Create inventory if not exists
if [ ! -f "inventories/production" ]; then
    echo "📝 Creating production inventory template..."
    cat > inventories/production << EOF
# VeloSim Production Inventory
# Replace YOUR_SERVER_IP with your actual server IP address

[velosim_servers]
velosim-prod-01 ansible_host=YOUR_SERVER_IP

[velosim_servers:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=$SSH_KEY_PATH
EOF
    echo "✅ Created inventories/production template"
fi

# Test Ansible configuration
echo "🔧 Testing Ansible configuration..."
if ansible-config dump &> /dev/null; then
    echo "✅ Ansible configuration is valid"
else
    echo "❌ Ansible configuration has issues"
fi

echo ""
echo "🎉 Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit inventories/production with your server IP"
echo "2. Edit group_vars/all.yml with your domain and users"
echo "3. Add the SSH public key to your server and GitHub"
echo "4. Run: ansible-playbook -i inventories/production deploy.yml"
echo ""
echo "For detailed instructions, see README.md"