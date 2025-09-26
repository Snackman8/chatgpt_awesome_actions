#!/bin/bash

# made for RHEL 9 + Debian/Ubuntu

SERVICE_NAME="chatgpt_awesome_actions.service"
APACHE_CONF="apache_chatgpt_awesome_actions.conf"
PIPX_HOME_DIR="/usr/local/pipx"
PIPX_BIN_DIR="/usr/local/bin"
SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME"

# --- Minimal OS detection for Apache layout ---
if [[ -d /etc/httpd ]]; then
  # RHEL/CentOS/Fedora
  APACHE_SERVICE="httpd"
  APACHE_CONF_DIR="/etc/httpd/conf.d"
  APACHE_CONF_PATH="$APACHE_CONF_DIR/$APACHE_CONF"
  APACHE_ENABLE_CMD=""
  APACHE_DISABLE_CMD=""
elif [[ -d /etc/apache2 ]]; then
  # Debian/Ubuntu
  APACHE_SERVICE="apache2"
  APACHE_SITES_AVAILABLE="/etc/apache2/sites-available"
  APACHE_SITES_ENABLED="/etc/apache2/sites-enabled"
  APACHE_CONF_PATH="$APACHE_SITES_AVAILABLE/$APACHE_CONF"
  APACHE_ENABLE_CMD="a2ensite $APACHE_CONF"
  APACHE_DISABLE_CMD="a2dissite $APACHE_CONF"
else
  echo "ERROR: Neither /etc/httpd nor /etc/apache2 found. Apache not installed?"
  exit 1
fi
# ---------------------------------------------

if [[ "$1" == "--uninstall" ]]; then
  echo "Uninstalling chatgpt_awesome_actions..."

  echo "Stopping and disabling systemd service..."
  sudo systemctl stop "$SERVICE_NAME"
  sudo systemctl disable "$SERVICE_NAME"

  echo "Removing systemd service file..."
  sudo rm -f "$SYSTEMD_PATH"
  sudo systemctl daemon-reload

  echo "Uninstalling the app using pipx..."
  sudo PIPX_HOME=$PIPX_HOME_DIR PIPX_BIN_DIR=$PIPX_BIN_DIR /usr/local/bin/pipx uninstall chatgpt_awesome_actions

  echo "Removing Apache proxy configuration..."
  if [[ -n "$APACHE_DISABLE_CMD" ]]; then
    sudo $APACHE_DISABLE_CMD || true
    sudo rm -f "$APACHE_CONF_PATH"
  else
    sudo rm -f "$APACHE_CONF_PATH"
  fi

  echo "Restarting Apache service..."
  sudo systemctl restart "$APACHE_SERVICE"

  echo "Uninstallation complete."
  exit 0
fi

echo "Installing chatgpt_awesome_actions..."

# Install the app (force to refresh if already installed)
echo "Installing the application using pipx..."
sudo PIPX_HOME=$PIPX_HOME_DIR PIPX_BIN_DIR=$PIPX_BIN_DIR /usr/local/bin/pipx install .. --include-deps --force

echo "Creating directories for generated files..."
sudo mkdir -p /var/lib/chatgpt_awesome_actions/generated_files

# Base venv path created by pipx for the dist "chatgpt-awesome-actions"
VENV_BASE="/usr/local/pipx/venvs/chatgpt-awesome-actions"

# Find the newest python3.* under lib (e.g., python3.9, python3.10, python3.11…)
PYVER="$(basename $(ls -d "$VENV_BASE"/lib/python3.* 2>/dev/null | sort -V | tail -n1))"
if [[ -z "$PYVER" ]]; then
  echo "ERROR: Could not find $VENV_BASE/lib/python3.* . Did pipx install succeed?" >&2
  exit 1
fi

PKG_DATA_DIR="$VENV_BASE/lib/$PYVER/site-packages/chatgpt_awesome_actions_datamodules/_static/files"

sudo rm -rf "$PKG_DATA_DIR"
sudo ln -s /var/lib/chatgpt_awesome_actions/generated_files "$PKG_DATA_DIR"

echo "Copying systemd service file..."
sudo cp "$SERVICE_NAME" /etc/systemd/system/
echo "Setting correct permissions for the service file..."
sudo chmod 644 "/etc/systemd/system/$SERVICE_NAME"

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "Enabling and starting the service..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Copying Apache proxy configuration..."
if [[ -n "$APACHE_ENABLE_CMD" ]]; then
  # Debian/Ubuntu: place in sites-available and enable

  # Copy vhost
  sudo cp "$APACHE_CONF" "$APACHE_CONF_PATH"

  # Ensure Debian-friendly settings
  sudo sed -i 's|/var/log/httpd|${APACHE_LOG_DIR}|g' "$APACHE_CONF_PATH"
  echo 'ServerName localhost' | sudo tee /etc/apache2/conf-available/servername.conf >/dev/null
  sudo a2enconf servername

  # **Enable required modules BEFORE enabling site**
  sudo a2enmod proxy proxy_http headers rewrite ssl

  # Enable site and validate
  sudo $APACHE_ENABLE_CMD
  sudo apache2ctl -t || { echo "Apache config test failed; fix errors above."; exit 1; }

  # Apply config
  sudo systemctl reload "$APACHE_SERVICE"
else
  # RHEL: drop-in conf.d and restart
  sudo cp "$APACHE_CONF" "$APACHE_CONF_PATH"
  sudo systemctl restart "$APACHE_SERVICE"
fi

echo "Installation complete."
