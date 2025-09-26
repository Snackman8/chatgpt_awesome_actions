#!/bin/bash
set -e

# Cross-distro installer for Ubuntu/Debian and RHEL/Fedora
# Enables auth (copies keys.db, starts monitor service, configures Apache)
#
# Expects the following files in the current directory:
#   - chatgpt_awesome_actions_with_auth.service
#   - chatgpt_awesome_actions_monitor.service
#   - apache_chatgpt_awesome_actions.conf
#
# Package name (pip) is assumed to be: chatgpt-awesome-actions

SERVICE_NAME="chatgpt_awesome_actions_with_auth.service"
MONITOR_SERVICE_NAME="chatgpt_awesome_actions_monitor.service"
APACHE_CONF="apache_chatgpt_awesome_actions.conf"

PIPX_HOME_DIR="/usr/local/pipx"
PIPX_BIN_DIR="/usr/local/bin"

SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME"
MONITOR_SYSTEMD_PATH="/etc/systemd/system/$MONITOR_SERVICE_NAME"

# --- Locate pipx (PATH, /usr/local/bin, /usr/bin) ---
PIPX_CMD="$(command -v pipx || true)"
if [[ -z "$PIPX_CMD" ]]; then
  for c in /usr/local/bin/pipx /usr/bin/pipx; do
    [[ -x "$c" ]] && PIPX_CMD="$c" && break
  done
fi
if [[ -z "$PIPX_CMD" ]]; then
  echo "ERROR: pipx not found. Install with 'apt/dnf install pipx' or 'python3 -m pip install --user pipx'." >&2
  exit 1
fi
sudo mkdir -p "$PIPX_HOME_DIR" "$PIPX_BIN_DIR"

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
  echo "ERROR: Neither /etc/httpd nor /etc/apache2 found. Is Apache installed?"
  exit 1
fi

# --- Uninstall flow ---
if [[ "$1" == "--uninstall" ]]; then
  echo "Uninstalling chatgpt_awesome_actions (with auth)..."

  echo "Stopping and disabling systemd services..."
  sudo systemctl stop "$MONITOR_SERVICE_NAME" || true
  sudo systemctl stop "$SERVICE_NAME" || true
  sudo systemctl disable "$MONITOR_SERVICE_NAME" || true
  sudo systemctl disable "$SERVICE_NAME" || true

  echo "Removing systemd service files..."
  sudo rm -f "$SYSTEMD_PATH" "$MONITOR_SYSTEMD_PATH"
  sudo systemctl daemon-reload

  echo "Uninstalling the app via pipx..."
  sudo PIPX_HOME=$PIPX_HOME_DIR PIPX_BIN_DIR=$PIPX_BIN_DIR "$PIPX_CMD" uninstall chatgpt_awesome_actions || true

  echo "Removing Apache proxy configuration..."
  if [[ -n "$APACHE_DISABLE_CMD" ]]; then
    sudo $APACHE_DISABLE_CMD || true
    sudo rm -f "$APACHE_CONF_PATH"
  else
    sudo rm -f "$APACHE_CONF_PATH"
  fi

  echo "Restarting Apache..."
  sudo systemctl restart "$APACHE_SERVICE"

  echo "Uninstallation complete."
  exit 0
fi

echo "Installing chatgpt_awesome_actions (with auth)..."

# --- Install/refresh the application via pipx ---
echo "Installing the application using pipx..."
sudo PIPX_HOME=$PIPX_HOME_DIR PIPX_BIN_DIR=$PIPX_BIN_DIR "$PIPX_CMD" install .. --include-deps --force

# --- Create persistent storage for generated files ---
echo "Creating directories for generated files..."
sudo mkdir -p /var/lib/chatgpt_awesome_actions/generated_files

# --- Determine venv + python version paths (created by pipx) ---
VENV_BASE="/usr/local/pipx/venvs/chatgpt-awesome-actions"
if [[ ! -d "$VENV_BASE" ]]; then
  echo "ERROR: Expected venv not found at $VENV_BASE . Did pipx install succeed?" >&2
  exit 1
fi

PYVER="$(basename $(ls -d "$VENV_BASE"/lib/python3.* 2>/dev/null | sort -V | tail -n1))"
if [[ -z "$PYVER" ]]; then
  echo "ERROR: Could not locate Python version folder under $VENV_BASE/lib/ ." >&2
  exit 1
fi

PKG_DATA_DIR="$VENV_BASE/lib/$PYVER/site-packages/chatgpt_awesome_actions_datamodules/_static/files"

# --- Link package static files to persistent dir ---
sudo rm -rf "$PKG_DATA_DIR"
sudo ln -s /var/lib/chatgpt_awesome_actions/generated_files "$PKG_DATA_DIR"

# --- Copy keys.db into venv root for auth-enabled runtime ---
if [[ -f "./keys.db" ]]; then
  echo "Copying keys.db into venv..."
  sudo cp ./keys.db "$VENV_BASE/keys.db"
  sudo chmod 600 "$VENV_BASE/keys.db" || true
else
  echo "WARNING: ./keys.db not found in the current directory."
  echo "Place your keys.db at: $VENV_BASE/keys.db before starting if required."
fi

# --- Install systemd units ---
echo "Copying systemd service files..."
sudo cp "$SERVICE_NAME" /etc/systemd/system/
sudo cp "$MONITOR_SERVICE_NAME" /etc/systemd/system/

echo "Setting permissions on service files..."
sudo chmod 644 "/etc/systemd/system/$SERVICE_NAME"
sudo chmod 644 "/etc/systemd/system/$MONITOR_SERVICE_NAME"

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling and starting services..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl enable "$MONITOR_SERVICE_NAME"
sudo systemctl restart "$MONITOR_SERVICE_NAME"

# --- Apache configuration ---
echo "Configuring Apache reverse proxy..."

if [[ -n "$APACHE_ENABLE_CMD" ]]; then
  # Debian/Ubuntu: copy to sites-available and enable
  sudo cp "$APACHE_CONF" "$APACHE_CONF_PATH"

  # Normalize log paths to Debian style if needed
  sudo sed -i 's|/var/log/httpd|${APACHE_LOG_DIR}|g' "$APACHE_CONF_PATH"

  # Ensure ServerName exists to silence warnings
  echo 'ServerName localhost' | sudo tee /etc/apache2/conf-available/servername.conf >/dev/null
  sudo a2enconf servername

  # Enable required modules BEFORE enabling the site
  sudo a2enmod proxy proxy_http headers rewrite ssl

  # Enable site and validate config
  sudo $APACHE_ENABLE_CMD
  sudo apache2ctl -t || { echo "Apache config test failed; see errors above."; exit 1; }

  # Apply configuration
  sudo systemctl reload "$APACHE_SERVICE"
else
  # RHEL/Fedora: drop into conf.d and restart
  sudo cp "$APACHE_CONF" "/etc/httpd/conf.d/$APACHE_CONF"
  sudo systemctl restart "$APACHE_SERVICE"
fi

echo "Installation with auth complete."
