# ChatGPT Awesome Actions

This repository provides installation scripts for deploying **ChatGPT Awesome Actions**.  
Below are step-by-step installation instructions for **Ubuntu** and **RHEL**.

---

## 📦 Prerequisites
- Git
- Python 3
- pip / pipx
- Apache2 (for serving)

---

## 🚀 Installation

### Ubuntu (20.04/22.04+)

```bash
# Update package lists
sudo apt-get update

# Install required packages
sudo apt-get install -y python3-pip apache2 pipx git

# Clone the repository
git clone https://github.com/Snackman8/chatgpt_awesome_actions

# Change into deployment directory
cd ~/chatgpt_awesome_actions/deployment

# Run the installer
sudo ./install.sh
```

---

### RHEL (8/9)

```bash
# Update package lists
sudo dnf update -y

# Install required packages
sudo dnf install -y python3-pip httpd pipx git

# Enable and start Apache (httpd)
sudo systemctl enable httpd
sudo systemctl start httpd

# Clone the repository
git clone https://github.com/Snackman8/chatgpt_awesome_actions

# Change into deployment directory
cd ~/chatgpt_awesome_actions/deployment

# Run the installer
sudo ./install.sh
```

---

## ✅ Verification
After installation:
1. Ensure Apache (httpd) is running:
   ```bash
   systemctl status apache2   # Ubuntu
   systemctl status httpd     # RHEL
   ```
2. Confirm the application is accessible at the configured URL or server IP.

---

## 🔒 Enable HTTPS with Let's Encrypt (Apache)

To secure your deployment with a free Let's Encrypt SSL certificate, install **Certbot** and configure Apache.

---

### Ubuntu

```bash
# Set your domain name
export DOMAIN=example.com

# Install Certbot and Apache plugin
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-apache

# Obtain and install a certificate
sudo certbot --apache -d $DOMAIN

# Test auto-renewal
sudo certbot renew --dry-run
```

---

### RHEL (8/9)

```bash
# Set your domain name
export DOMAIN=example.com

# Enable EPEL repository
sudo dnf install -y epel-release

# Install Certbot and Apache plugin
sudo dnf install -y certbot python3-certbot-apache

# Obtain and install a certificate
sudo certbot --apache -d $DOMAIN

# Test auto-renewal
sudo certbot renew --dry-run
```

---

### Notes
- Certificates are stored in `/etc/letsencrypt/live/$DOMAIN/`.
- Auto-renewal is handled by a systemd timer (`certbot.timer`) by default.
- To check the renewal service:
  ```bash
  systemctl list-timers | grep certbot
  ```



## 🛠️ Uninstall
To uninstall, run the installer with the `--uninstall` flag:

```bash
cd ~/chatgpt_awesome_actions/deployment
sudo ./install.sh --uninstall
```
