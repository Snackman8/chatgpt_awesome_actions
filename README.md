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

## 📖 Notes
- For custom configurations, review `deployment/install.sh` before running.  
- Logs are typically located in:
  - `/var/log/apache2/` (Ubuntu)
  - `/var/log/httpd/` (RHEL)

---

## 🛠️ Uninstall
To uninstall, run the installer with the `--uninstall` flag:

```bash
cd ~/chatgpt_awesome_actions/deployment
sudo ./install.sh --uninstall
```
