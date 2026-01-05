#!/bin/bash
# Setup script for GitHub Actions deployment user
# Run this script on your deployment server as root or with sudo

set -e

DEPLOY_USER="github-deploy"
DEPLOY_HOME="/home/${DEPLOY_USER}"

echo "Setting up deployment user: ${DEPLOY_USER}"

# Create deployment user (if doesn't exist)
if id "$DEPLOY_USER" &>/dev/null; then
    echo "User ${DEPLOY_USER} already exists"
else
    useradd -m -s /bin/bash "$DEPLOY_USER"
    echo "User ${DEPLOY_USER} created"
fi

# Add user to docker group (so they can run docker commands without sudo)
usermod -aG docker "$DEPLOY_USER"

# Create .ssh directory
mkdir -p "${DEPLOY_HOME}/.ssh"
chmod 700 "${DEPLOY_HOME}/.ssh"

# Generate SSH key pair (this will be used by GitHub Actions)
echo ""
echo "=== GENERATING SSH KEY PAIR ==="
ssh-keygen -t ed25519 -f "${DEPLOY_HOME}/.ssh/github_actions" -N "" -C "github-actions-deployment"

# Add public key to authorized_keys
cat "${DEPLOY_HOME}/.ssh/github_actions.pub" >> "${DEPLOY_HOME}/.ssh/authorized_keys"
chmod 600 "${DEPLOY_HOME}/.ssh/authorized_keys"

# Fix ownership
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_HOME}/.ssh"

echo ""
echo "=== SETUP COMPLETE ==="
echo ""
echo "Next steps:"
echo "1. Copy the PRIVATE key below and add it to GitHub Secrets as 'DEPLOY_SSH_KEY'"
echo ""
echo "--- PRIVATE KEY (add to GitHub Secrets) ---"
cat "${DEPLOY_HOME}/.ssh/github_actions"
echo "--- END PRIVATE KEY ---"
echo ""
echo "2. Add these secrets to your GitHub repository:"
echo "   - DEPLOY_HOST: <your-server-ip-or-hostname>"
echo "   - DEPLOY_USER: ${DEPLOY_USER}"
echo "   - DEPLOY_SSH_KEY: <paste the private key above>"
echo ""
echo "3. The deployment user can now run docker commands without sudo"
echo ""
echo "Public key (for reference):"
cat "${DEPLOY_HOME}/.ssh/github_actions.pub"
