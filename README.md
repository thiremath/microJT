# 🚀 GS Job Tracker

A smart website tracker that monitors Goldman Sachs job listings and sends Telegram alerts when changes are detected.

## ✨ Features

- **Smart Change Detection**: Extracts meaningful job information instead of just hash comparisons
- **Telegram Notifications**: Sends detailed alerts with job titles, locations, and counts
- **Cloud-Ready**: Optimized for Render deployment
- **Robust Error Handling**: Multiple fallback methods for job extraction
- **Detailed Logging**: Comprehensive logging for debugging

## 📱 Sample Telegram Messages

When changes are detected, you'll receive messages like:

```
🚨 CHANGE DETECTED
⏰ 2024-01-15 14:30:25

GS Job Listings Updated!

🔗 View Updated Listings

📊 Current Status:
• Total Jobs: 62
• Showing: 20

📝 Changes Detected:

📈 New jobs added! Total increased from 59 to 62

🆕 New positions:
• Software Engineer - Machine Learning (Dallas)
• Associate - Data Engineering (Salt Lake City)
• Analyst - Backend Development (New York)
```

## 🚀 Render Deployment

### Quick Deploy Steps:

1. **Push your code to GitHub**
2. **Go to [render.com](https://render.com)**
3. **Sign up with GitHub account**
4. **Click "New +" → "Background Worker"**
5. **Connect your GitHub repository**
6. **Configure:**
   - **Name:** `gs-job-tracker`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python tracker.py`
   - **Plan:** `Free`
7. **Click "Create Background Worker"**

### Environment Variables (Optional):

In Render dashboard, add these environment variables:
- `TELEGRAM_BOT_TOKEN` = your bot token
- `TELEGRAM_CHAT_ID` = your chat ID
- `CHECK_INTERVAL` = 600 (or your preferred interval)

## 📁 Project Structure

```
website_tracker/
├── tracker.py              # Main tracker script
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
├── gs_jobs_hash.txt       # Hash storage (auto-created)
├── gs_jobs_data.txt       # Job data storage (auto-created)
└── README.md              # This file
```

## ⚙️ Configuration

**Environment Variables (Required):**

You must set these environment variables in Render dashboard:

- `TELEGRAM_BOT_TOKEN` = Your Telegram bot token
- `TELEGRAM_CHAT_ID` = Your Telegram chat ID
- `CHECK_INTERVAL` = 600 (optional, defaults to 10 minutes)

**Local Development:**

For local testing, create a `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
CHECK_INTERVAL=600
```

**Target URL:**
```python
URL = "https://higher.gs.com/results?..."
```

## 🔧 Setup Instructions

### 1. Create Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`
3. Follow instructions to create bot
4. Copy the bot token to `tracker.py`

### 2. Get Your Chat ID

1. Message your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find your `chat_id` in the response
4. Add it to `tracker.py`

### 3. Deploy to Render

1. Push code to GitHub
2. Follow the deployment steps above
3. Monitor logs in Render dashboard
4. Check Telegram for startup message

## 🧪 Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run tracker
python tracker.py
```

## 📊 What Gets Tracked

- **Job Count Changes**: Total number of jobs increases/decreases
- **New Job Titles**: Specific new positions added
- **Removed Jobs**: Positions that are no longer listed
- **Location Changes**: Job location updates
- **Content Updates**: Any changes to the job listings page

## 🔍 Troubleshooting

### Common Issues:

1. **Build Failures**: Check that `requirements.txt` is correct
2. **Runtime Errors**: Check logs in Render dashboard
3. **Telegram Notifications**: Verify bot token and chat ID
4. **Chrome/Selenium Issues**: Code includes fallback methods

### Render Free Tier Limits:

- **750 hours/month** (31 days)
- **Background workers** supported
- **Automatic restarts** on failures
- **GitHub integration** for auto-deploy

## 📈 Monitoring

The tracker will:
- ✅ Send startup notification
- ✅ Monitor every 10 minutes (configurable)
- ✅ Send detailed change alerts
- ✅ Handle errors gracefully
- ✅ Save job data for comparison

## 🛡️ Error Handling

- **Network Issues**: Automatic retry and error reporting
- **Page Changes**: Multiple fallback extraction methods
- **Telegram Failures**: Detailed error logging
- **Cloud Environment**: Chrome driver auto-installation

## 📝 License

MIT License - Feel free to modify and use for your own projects!

---

**Happy Job Hunting! 🎯** 