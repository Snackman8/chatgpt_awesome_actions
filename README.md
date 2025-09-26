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
---

## ✅ Post-Install Validation (Bootstrap, No Auth)

After the initial install (`./install.sh`) **before** enabling auth, verify the service is reachable.

> Expected: HTTP **200** (OK)

### 1) Ensure `$DOMAIN` is set
```bash
export DOMAIN=example.com
```

### 2) Test the public endpoint
```bash
curl -s -o /dev/null -w "%{http_code}\n" -L "https://$DOMAIN/chatgpt_awesome_actions/actions"
```

**Expected output:**
```
200
```

### Why 200?
- In **bootstrap (no-auth) mode**, the `/chatgpt_awesome_actions/actions` endpoint is intentionally open to confirm the app and Apache proxy are wired correctly.
- A **200 OK** indicates:
  - The systemd service is running and serving the endpoint.
  - Apache virtual host / proxy rules are active.
  - (If using HTTPS) Any HTTP→HTTPS redirects have been followed (`curl -L`).
- This check is a basic **liveness/readiness** probe; it does **not** perform an authenticated action call.

---

## 🔑 Creating a New API Key

Before ChatGPT can call your actions, you must generate an **API key**.  
This key will be used by ChatGPT to authenticate every action call against your deployment.  
Without a valid API key, action requests will be rejected.

API keys are managed with the `datahub_api_key_manager` tool. This tool stores keys in a local SQLite database.

---

### Steps

1. Run the key manager (using the deployment database path):
   ```bash
   datahub_api_key_manager --db_path ~/chatgpt_awesome_actions/deployment/keys.db
   ```

2. From the **Key Management Console**, choose option **1. Add Key**:
   ```
   Key Management Console
   1. Add Key
   2. View Keys
   3. Update Key
   4. Delete Key
   5. Exit
   Enter your choice: 1
   ```

3. Follow the prompts:
   - **Allowed path regex** → press Enter to allow all (`.*`)
   - **Start date / End date** → leave blank for no restriction
   - **API key** → press Enter to auto-generate
   - **Note** → optional description for the key

4. Example output:
   ```
   Key added successfully.
   API Key: 1Az4obON6dLUpcuQuGUsjvsZeRq3iTNP
   ```

   ⚠️ Save this API key securely — you will need to provide it to ChatGPT so it can authenticate action calls.

5. To confirm the key was added, select **2. View Keys**:
   ```
   ID    | Allowed Path Regex | Start Date | End Date | API Key                            | Note
   ------------------------------------------------------------------------------------------------------
   1     | .*                 |            |          | 1Az4obON6dLUpcuQuGUsjvsZeRq3iTNP   |
   ```

6. When finished, choose **5. Exit**.

---

### Notes
- The generated API key must be provided to ChatGPT when configuring actions.  
- By default, keys do not expire unless a start and/or end date is specified.  
- The SQLite database is located at:
  ```
  ~/chatgpt_awesome_actions/deployment/keys.db
  ```
  Ensure this file is backed up securely.

---

## 🚀 Deploying with the API Key

Once the API key has been generated, you must redeploy the system with authentication enabled.

1. **Uninstall the bootstrap deployment**:
   ```bash
   cd ~/chatgpt_awesome_actions/deployment
   sudo ./install.sh --uninstall
   ```

2. **Reinstall with authentication enabled**:
   ```bash
   cd ~/chatgpt_awesome_actions/deployment
   sudo ./install_with_auth.sh
   ```

After this step, your deployment will require the API key for all ChatGPT action calls.

---

## ✅ Post-Install Validation (Auth Mode)

After installing with authentication (`./install_with_auth.sh`), verify that unauthenticated requests are **rejected**.

> Expected: HTTP **400** (Bad Request) when no API key is provided.

### 1) Ensure `$DOMAIN` is set (if not already)
```bash
export DOMAIN=example.com
```

### 2) Test the public endpoint (no auth)
```bash
curl -s -o /dev/null -w "%{http_code}\n" -L "https://$DOMAIN/chatgpt_awesome_actions/actions"
```

**Expected output:**
```
400
```

### Why 400?
The actions endpoint requires authenticated requests and/or required parameters. Hitting it without credentials should return **400** to indicate an invalid/missing request context.

---

# Create a GPT Action with Custom API Key Auth (`x-api-key`)

## Steps (before schema)
1. Create a new GPT → Explore GPTs → Create → name/description.
2. Add an Action → Actions → Add Action → Import from schema → paste the schema below.

---

## OpenAPI schema (paste as-is; update the last URL after)
```
openapi: 3.1.0
info:
  title: Dynamic API
  version: 1.0.0
  description: API with dynamic function handlers
servers:
  - url: https://<YOUR_DOMAIN>/chatgpt_awesome_actions/
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: x-api-key
security:
  - ApiKeyAuth: []
paths:
  /actions/echo:
    post:
      description: Echoes back a message as a test.
      operationId: actions__echo
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                msg:
                  type: string
                  description: The message to be returned.
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                type: object
                description: 'A dictionary containing the response with:'
                properties:
                  body:
                    type: string
                    description: The echoed message.
                  content-type:
                    type: string
                    description: The MIME type of the response.
  /actions/exec_python_code:
    post:
      description: >
        Executes Python code on a remote machine. Any strings in the return
        value that start with `/tmp/` will automatically be converted to
        published URLs, and the corresponding temporary files will be deleted
        after publication.
      operationId: actions__exec_python_code
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                code:
                  type: string
                  description: >
                    The Python code to execute. The code must assign a value to
                    `__retval__`.
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                type: object
                description: 'A dictionary containing the execution result with:'
                properties:
                  body:
                    type: string
                    description: >
                      The return value of the executed Python code. Any file paths
                      from `/tmp/`.
                  content-type:
                    type: string
                    description: The MIME type of the response, dynamically set.
```
---

## Steps (after schema)
3. Change the server URL:
   - In `servers`, replace `<YOUR_DOMAIN>` with your domain.
   - Keep `/chatgpt_awesome_actions/` if that’s where your service is mounted.
4. Configure Authentication (matches the UI):
   - Authentication Type: API Key
   - Auth Type: Custom
   - Custom Header Name: x-api-key
   - API Key: paste your generated key
   - Save

---

## Test (inside the Action tester)
- Call POST `/actions/echo` with:
{ "msg": "hello" }
- Expect 200 OK with the echoed message in `body`.

---

## 🛠️ Uninstall
To uninstall, run the installer with the `--uninstall` flag:

```bash
cd ~/chatgpt_awesome_actions/deployment
sudo ./install.sh --uninstall
```
