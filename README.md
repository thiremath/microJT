# 🚀 Generic Website Tracker

A smart, generic website tracker that monitors any website for changes and sends Telegram alerts when updates are detected. Supports monitoring multiple websites simultaneously.

## ✨ Features

- **Generic Website Monitoring**: Monitor any website, not just job listings
- **Multiple Website Support**: Track multiple websites simultaneously
- **Smart Change Detection**: Detects content changes, link additions/removals, and count changes
- **Telegram Notifications**: Sends detailed alerts with change descriptions
- **Cloud-Ready**: Optimized for Render deployment
- **Robust Error Handling**: Comprehensive error handling and logging
- **Configurable**: Easy JSON-based configuration

## 📱 Sample Telegram Messages

When changes are detected, you'll receive messages like:

```
🚨 CHANGE DETECTED
⏰ 2024-01-15 14:30:25

Website Updated: Goldman Sachs Jobs

🔗 View Website

📊 Current Status:
• Page Title: Goldman Sachs Careers
• Content Size: 45230 characters
• Links Found: 25

📝 Changes Detected:

📊 Content size changed: 45230 → 45890 characters
🔗 New links found: 3
📈 Counts changed: {'matches': [('20', '59')]} → {'matches': [('20', '62')]}
```

## 🚀 Render Deployment

### Quick Deploy Steps:

1. **Push your code to GitHub**
2. **Go to [render.com](https://render.com)**
3. **Sign up with GitHub account**
4. **Click "New +" → "Web Service"** (Free tier)
5. **Connect your GitHub repository**
6. **Configure:**
   - **Name:** `website-tracker`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Plan:** `Free`
7. **Set Environment Variables:**
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `TELEGRAM_CHAT_ID` = your chat ID
8. **Click "Create Web Service"**

## 📁 Project Structure

```
website_tracker/
├── tracker.py              # Main tracker script (generic)
├── app.py                  # Web service wrapper for Render
├── config.json             # Website configuration
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── data/                   # Auto-generated data files
│   ├── Website_Name_hash.txt
│   └── Website_Name_data.json
└── README.md               # This file
```

## ⚙️ Configuration

### 1. Create `config.json`

Create a `config.json` file with your website configurations:

```json
{
  "websites": [
    {
      "name": "Goldman Sachs Jobs",
      "url": "https://higher.gs.com/results?...",
      "enabled": true,
      "check_interval": 600,
      "description": "Goldman Sachs Software Engineering Jobs"
    },
    {
      "name": "Another Website",
      "url": "https://example.com/jobs",
      "enabled": true,
      "check_interval": 300,
      "description": "Example job board"
    }
  ],
  "telegram": {
    "bot_token": null,
    "chat_id": null
  },
  "global_settings": {
    "default_check_interval": 600,
    "page_load_wait": 8,
    "extract_content": true
  }
}
```

### 2. Environment Variables

**Required:**
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID

**Optional:**
- `CONFIG_FILE` - Path to config file (default: `config.json`)
- `CHECK_INTERVAL` - Default check interval in seconds

### 3. Website Configuration Options

Each website in `config.json` can have:
- **`name`** (required): Display name for the website
- **`url`** (required): URL to monitor
- **`enabled`** (optional): Enable/disable monitoring (default: `true`)
- **`check_interval`** (optional): Check interval in seconds (default: 600)
- **`description`** (optional): Description shown in notifications

## 🔧 Setup Instructions

### 1. Telegram Bot (Already Created!)

Your bot is already created: [@gs_tracker_bot](https://t.me/gs_tracker_bot)

**Bot Token:** `7623240757:AAHiPQ8QuwZN8SYRvtCV14RwvF04nCTwP3E`

### 2. Get Your Chat ID

1. **Message your bot** on Telegram: [@gs_tracker_bot](https://t.me/gs_tracker_bot)
2. **Visit this URL** (replace with your bot token if needed):
   ```
   https://api.telegram.org/bot7623240757:AAHiPQ8QuwZN8SYRvtCV14RwvF04nCTwP3E/getUpdates
   ```
3. **Find your `chat_id`** in the JSON response (look for `"chat":{"id":123456789}`)

### 3. Create .env File

Create a `.env` file in the project root:

```bash
TELEGRAM_BOT_TOKEN=7623240757:AAHiPQ8QuwZN8SYRvtCV14RwvF04nCTwP3E
TELEGRAM_CHAT_ID=your_chat_id_here
CHECK_INTERVAL=600
```

### 4. Configure Websites

Your `config.json` already includes 5 job boards:
- Goldman Sachs
- Barclays
- Microsoft
- Apple
- PayPal

You can edit `config.json` to add/remove websites or adjust check intervals.

### 5. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run tracker
python tracker.py
```

The tracker will start monitoring all enabled websites and send Telegram notifications when changes are detected!

## 🧪 Testing Locally

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# .env file
TELEGRAM_BOT_TOKEN=7623240757:AAHiPQ8QuwZN8SYRvtCV14RwvF04nCTwP3E
TELEGRAM_CHAT_ID=your_chat_id_here
CHECK_INTERVAL=600
```

**To get your Chat ID:**
1. Message your bot on Telegram: [@gs_tracker_bot](https://t.me/gs_tracker_bot)
2. Visit: `https://api.telegram.org/bot7623240757:AAHiPQ8QuwZN8SYRvtCV14RwvF04nCTwP3E/getUpdates`
3. Find your `chat_id` in the response (look for `"chat":{"id":123456789}`)

### 3. Run the Tracker

```bash
# Run tracker (monitors all websites from config.json)
python tracker.py
```

The tracker will:
- Load websites from `config.json`
- Monitor all enabled websites simultaneously
- Send Telegram notifications when changes are detected
- Store data in `data/` directory

## 📊 What Gets Tracked

- **Content Changes**: Detects changes in page content
- **Link Changes**: New links added or removed
- **Count Changes**: Changes in count patterns (results, items, etc.)
- **Page Title Changes**: Changes in page title
- **Content Size**: Changes in overall content size

## 🔍 Troubleshooting

### Common Issues:

1. **Build Failures**: Check that `requirements.txt` is correct
2. **Runtime Errors**: Check logs in Render dashboard
3. **Telegram Notifications**: Verify bot token and chat ID
4. **Chrome/Selenium Issues**: Code includes fallback methods
5. **Config Errors**: Verify `config.json` is valid JSON

### Render Free Tier Limits:

- **750 hours/month** (31 days)
- **Web services** supported
- **Automatic restarts** on failures
- **GitHub integration** for auto-deploy

## 📈 Monitoring Multiple Websites

The tracker supports monitoring multiple websites:

- **Single Website**: Simple loop monitoring
- **Multiple Websites**: Each website runs in its own thread
- **Independent Intervals**: Each website can have its own check interval
- **Separate Data Files**: Each website has its own hash and data files

## 🛡️ Error Handling

- **Network Issues**: Automatic retry and error reporting
- **Page Changes**: Generic extraction methods work with any website
- **Telegram Failures**: Detailed error logging
- **Cloud Environment**: Chrome driver auto-installation
- **Per-Website Errors**: Errors for one website don't affect others

## 📝 Example Configurations

### Job Board Monitoring
```json
{
  "name": "Tech Jobs",
  "url": "https://techjobs.com/listings",
  "check_interval": 300
}
```

### News Website
```json
{
  "name": "Tech News",
  "url": "https://technews.com/latest",
  "check_interval": 1800
}
```

### Product Page
```json
{
  "name": "Product Availability",
  "url": "https://store.com/product/123",
  "check_interval": 60
}
```

## 📝 License

MIT License - Feel free to modify and use for your own projects!

---

**Happy Website Monitoring! 🎯**
