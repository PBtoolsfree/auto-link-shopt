# ⚡ GPLinks Telegram & Discord Affiliate Deal Forwarder

A premium, fully-automated deal-forwarding system designed to watch a private Telegram source channel, automatically detect shared links/media posts, shorten all destination product links using the **GPLinks Developers API**, and broadcast the transformed premium posts (with photo + formatted description + link button) to a public Telegram channel and Discord server in real-time.

---

## ✨ Features

- **No Complex SMS Code/Phone Authentications:** Uses a standard, dedicated Telegram Bot Token and Discord Bot Token / Webhook, eliminating login errors.
- **Dynamic GPLinks API GET Request Integration:** Fast, reliable URL shortening via GPLinks.
- **Media (Photo) Support:** Instantly fetches original images, keeping post styling identical to the source channel.
- **Discord Rich Embeds & Buttons:** Posts clean, responsive, card-like embeddings with a custom call-to-action shop button.
- **Vibrant Control Dashboard:** A fully protected, glassmorphic dark mode panel allowing you to start/stop the bot, monitor metrics, save settings, and view logs dynamically in your browser.
- **Enterprise VPS Auto-Installer (`install.sh`):** Installs system dependencies, configures an isolated python environment, securely provisions default credentials, and sets up a robust systemd background service.

---

## 🚀 Setup & Launch Instructions

### Step 1: Telegram Bot Creation & Config
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the instructions to get your **Telegram Bot Token** (e.g. `1234567890:ABC...`).
3. Add your new Bot to **both** your **Source Channel** (private) and **Destination Channel** (public) as an **Administrator** with *Post Messages* permissions.
4. Get your Channel usernames (e.g. `@my_source`) or numeric IDs (e.g. `-1002222333444`). *Hint: You can forward a post from your channel to [@username_to_id_bot](https://t.me/username_to_id_bot) to get the numeric ID.*

### Step 2: Discord Integration Config
- **If using Discord Webhook Mode (Recommended):**
  1. Open your Discord server and right-click on the target text channel.
  2. Select **Edit Channel** ➔ **Integrations** ➔ **Webhooks** ➔ **Create Webhook**.
  3. Copy the **Webhook URL** and keep it ready.
- **If using Discord Bot Mode:**
  1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
  2. Create a **New Application**, navigate to the **Bot** tab, and copy your **Bot Token**.
  3. Under OAuth2 ➔ URL Generator, select `bot` scope and `Send Messages`, `Embed Links`, `Attach Files` permissions. Use the generated link to invite the Bot to your Discord Server.
  4. Enable Developer Mode on Discord to copy your target **Channel ID**.

---

## 💻 Running the Application

### Option A: Windows Local Launch
1. Open the project folder in your terminal or File Explorer.
2. Double-click the [start.bat](file:///C:/Users/PRADIP/.gemini/antigravity-ide/scratch/gplinks-affiliate-bot/start.bat) file (it will automatically create virtual environment `.venv`, update pip dependencies, and start the local dashboard).
3. Open your web browser and navigate to: `http://localhost:8000`
4. Enter the default gateway portal secret password: `admin123`.

### Option B: Oracle Cloud & Linux VPS Deployment (Recommended)
We have built a premium, fully-automated installation script (`install.sh`) specifically designed for Oracle Cloud, AWS, or any Linux VPS. It takes care of packages, creates a systemd service, auto-generates a secure password, and displays your dashboard connection info.

1. Clone your repository onto the VPS:
   ```bash
   git clone https://github.com/PBtoolsfree/auto-link-shopt.git
   cd auto-link-shopt
   ```
2. Make the installer executable and run it with sudo:
   ```bash
   chmod +x install.sh
   sudo ./install.sh
   ```
3. Once completed, the installer will print a beautiful deployment report containing:
   - **Web Dashboard URL:** `http://<your_vps_ip>:8000`
   - **Generated Password:** A secure, unique key dynamically generated for your server.

#### 💡 Managing the VPS Background Daemon (systemd)
The installer configures the deal forwarder to run in the background as a native systemd service (`gplinks-bot.service`) which automatically starts on boot.

- **Check logs in real-time:**
  ```bash
  sudo journalctl -u gplinks-bot -f -n 50
  ```
- **Check service status:**
  ```bash
  sudo systemctl status gplinks-bot
  ```
- **Restart the bot service:**
  ```bash
  sudo systemctl restart gplinks-bot
  ```
- **Stop the bot service:**
  ```bash
  sudo systemctl stop gplinks-bot
  ```

#### ⚠️ Oracle Cloud Firewall Configurations
To access the dashboard from your browser, make sure Port **8000** is open under ingress rules in your Oracle Cloud Subnet Security List, and allow it on your VPS operating system firewall:
- **For Ubuntu/Debian:**
  ```bash
  sudo ufw allow 8000/tcp
  ```
- **For Oracle Linux/RedHat:**
  ```bash
  sudo firewall-cmd --permanent --add-port=8000/tcp
  sudo firewall-cmd --reload
  ```

---

## 🛠️ Subsystem Diagnostics

All system operations write active metrics, failures, or successes directly to `gplinks_bot.log`. The terminal dashboard polls these logs and status counters every **3 seconds** dynamically to show you exact operating stats!

- **Deals Caught:** Increases every time a new deal post containing links/media is caught from your private Source Channel.
- **TG Sent / Discord Sent:** Increases on successful broadcasts.

---
*Powered by PB Hero Bot Control Systems.*
