# Rinox Sentinel 🛡️

**Rinox Sentinel** is a high-performance, AI-powered Discord security and moderation platform. It utilizes advanced AI models to scan messages, images, and attachments in real-time, providing an elite level of protection for your community.

---

## 🚀 Features

### 🤖 AI-Powered Protection
- **Multi-Provider AI:** Supports OpenAI, Anthropic, Google Gemini, Groq, DeepSeek, and more.
- **Failover Logic:** Automatically switches to fallback AI providers if the primary one is down.
- **AI Vision:** Analyzes images to detect phishing pages, fake login screens, and malicious content.
- **OCR Scanning:** Reads text inside images to catch hidden scams and forbidden words.

### 🔒 Advanced Security
- **Anti-Raid:** Detects and prevents mass join attacks.
- **Anti-Spam:** Advanced pattern matching to block spam.
- **Link & Invite Filtering:** Scans URLs for phishing and malicious domains.
- **Attachment Scanning:** Blocks dangerous file types and suspicious uploads.

### 🛡️ Smart Moderation
- **Dashboard Interface:** Configure all settings through a modern, button-based UI.
- **Automated Actions:** Auto-warn, auto-timeout, or auto-ban based on AI risk scores.
- **Detailed Logs:** Keep track of every security event and moderation action.

---

## 🛠️ Installation

### Prerequisites
- Python 3.10 or higher
- PostgreSQL Database
- Redis Server
- Tesseract OCR (for image scanning)

### Steps
1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/rinox-sentinel.git
   cd rinox-sentinel
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Open `.env` and fill in your credentials (see [Configuration](#-configuration) below).

4. **Run the Bot:**
   ```bash
   python main.py
   ```

---

## ⚙️ Configuration (.env)

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Your Discord Bot Token. |
| `DATABASE_URL` | PostgreSQL connection string (`postgresql://user:pass@host/db`). |
| `REDIS_URL` | Redis connection string (`redis://localhost:6379/0`). |
| `OPENAI_API_KEY` | API Key for OpenAI models. |
| `ANTHROPIC_API_KEY` | API Key for Claude models. |
| `GROQ_API_KEY` | API Key for high-speed Llama models. |
| `ENCRYPTION_KEY` | A 32-byte key for encrypting sensitive data in the DB. |
| `VIRUSTOTAL_API_KEY` | (Optional) For file attachment scanning. |

---

## ⌨️ Command Reference

### 🛠️ Setup & System
- `/setup` - Open the main dashboard to configure the bot.
- `/status` - Check bot latency, uptime, and system health.
- `/help` - Show a list of all available commands.
- `/version` - View the current version and build info.
- `/test` - Test the connection to all configured AI providers.
- `/reset` - Wipe all guild settings and reset to defaults.
- `/debug` - View technical debug information (Admin only).

### 🤖 AI Configuration
- `/provider` - Quickly switch the primary AI provider (e.g., OpenAI to Groq).
- `/model` - Change the specific model being used (e.g., `gpt-4o`).
- `/apikey` - Update the API key for the current provider.
- `/baseurl` - Set a custom API endpoint (e.g., for local LLMs).
- `/ai-info` - View detailed AI configuration for the server.

### 📝 Logging System (`/log` Group)
- `/log set-channel <channel>` - Set the target channel where security & moderation events are logged.
- `/log show` - View current log configuration and status.
- `/log remove` - Disable logging completely for the server.

### ⚙️ Automation & Rules (`/automate` Group)
- `/automate threshold <action> <score>` - Set the risk threshold (1-100) to trigger actions (`delete`, `warn`, `lockdown`).
- `/automate toggle-module <module> <enabled>` - Enable or disable individual protection modules (Anti-Raid, Anti-Spam, Anti-Link, etc.).
- `/automate show` - View active thresholds and protection status for all modules.

### 🔒 Security & Scanning
- `/scan <type> [target]` - Manually scan a message, user, or image.
- `/security` - Configure anti-raid, anti-spam, and scanning features.
- `/whitelist` - Manage the list of trusted users/roles.
- `/blacklist` - Block specific users or domains from the server.

### 🛡️ Moderation
- `/warn <user> <reason>` - Issue a formal warning to a member.
- `/mute <user> <duration> [reason]` - Mute a user for a set time.
- `/kick <user> [reason]` - Kick a member from the server.
- `/ban <user> [reason]` - Permanently ban a member.
- `/history <user>` - View a user's moderation history and risk score.

### 📊 Analytics & Backups
- `/analytics` - View real-time server security statistics.
- `/report` - Generate a weekly or monthly security report.
- `/backup` - Create a secure backup of server settings and roles.
- `/restore` - Restore server settings from a previous backup.

---

## 🔬 Security Pipeline

Every message and attachment goes through the **Rinox Pipeline**:
1. **Fast Check:** Regex and keyword matching for known threats.
2. **Metadata Scan:** Checks account age, join rate, and user profile.
3. **OCR/QR Analysis:** Extracts text and URLs from images.
4. **AI Deep Scan:** The content is sent to the AI for intent analysis.
5. **Risk Scoring:** A risk score (0-100) is calculated.
6. **Auto-Action:** If the score exceeds thresholds, the bot executes the configured action (Delete/Warn/Ban).

---

## 🧰 Tech Stack
- **Language:** Python 3.10+
- **Library:** `discord.py` (v2.3+)
- **Database:** PostgreSQL (`asyncpg`)
- **Cache:** Redis (`redis-py`)
- **AI Interface:** `httpx`, `openai`, `anthropic`
- **Image Processing:** `Pillow`, `pytesseract`, `pyzbar`
