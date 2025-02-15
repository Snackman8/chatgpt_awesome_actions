#!/bin/bash

# made for RHEL 9

SERVICE_NAME="chatgpt_awesome_actions_with_auth.service"
APACHE_CONF="apache_chatgpt_awesome_actions.conf"
PIPX_HOME_DIR="/usr/local/pipx"
PIPX_BIN_DIR="/usr/local/bin"
SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME"
APACHE_CONF_PATH="/etc/httpd/conf.d/$APACHE_CONF"

if [[ "$1" == "--uninstall" ]]; then
    echo "Uninstalling chatgpt_awesome_actions..."

    echo "Stopping and disabling systemd service..."
    sudo systemctl stop $SERVICE_NAME
    sudo systemctl disable $SERVICE_NAME

    echo "Removing systemd service file..."
    sudo rm -f $SYSTEMD_PATH
    sudo systemctl daemon-reload

    echo "Uninstalling the app using pipx..."
    sudo PIPX_HOME=$PIPX_HOME_DIR PIPX_BIN_DIR=$PIPX_BIN_DIR /usr/local/bin/pipx uninstall chatgpt_awesome_actions

    echo "Removing Apache proxy configuration..."
    sudo rm -f $APACHE_CONF_PATH

    echo "Restarting Apache service..."
    sudo systemctl restart httpd

    echo "Uninstallation complete."
    exit 0
fi

echo "Installing chatgpt_awesome_actions..."

# Install the app
echo "Installing the application using pipx..."
sudo PIPX_HOME=$PIPX_HOME_DIR PIPX_BIN_DIR=$PIPX_BIN_DIR /usr/local/bin/pipx install .. --include-deps

echo "Creating directories for generated files..."
sudo mkdir -p /var/lib/chatgpt_awesome_actions/generated_files
sudo rm -rf /usr/local/pipx/venvs/chatgpt-awesome-actions/lib/python3.9/site-packages/chatgpt_awesome_actions_datamodules/_static/files
sudo ln -s /var/lib/chatgpt_awesome_actions/generated_files /usr/local/pipx/venvs/chatgpt-awesome-actions/lib/python3.9/site-packages/chatgpt_awesome_actions_datamodules/_static/files

echo "Copying systemd service file..."
sudo cp $SERVICE_NAME /etc/systemd/system/

echo "Setting correct permissions for the service file..."
sudo chmod 644 /etc/systemd/system/$SERVICE_NAME

echo "Copying keys.db..."
cp keys.db /usr/local/pipx/venvs/chatgpt-awesome-actions/keys.db

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling and starting the service..."
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

echo "Copying Apache proxy configuration..."
sudo cp $APACHE_CONF $APACHE_CONF_PATH

echo "Restarting Apache service..."
sudo systemctl restart httpd

echo "Installation complete."
