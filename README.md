# 🚀 Job Posting Tracker

A smart job posting tracker that monitors multiple job boards and sends Telegram alerts when new job postings are detected. Perfect for tracking job opportunities from companies like Goldman Sachs, Apple, Microsoft, Barclays, and PayPal.

## ✨ Features

- **Job-Specific Tracking**: Focused on detecting new job postings, not just website changes
- **Multiple Job Boards**: Track multiple job boards simultaneously
- **Website-Specific Patterns**: Uses optimized URL patterns for each job board:
  - **Goldman Sachs**: `/roles/` pattern
  - **Apple**: `/details/` pattern
  - **Barclays, Microsoft, PayPal**: `/job` pattern
- **Smart Change Detection**: Only alerts when new jobs are actually posted
- **Telegram Notifications**: Sends detailed alerts with job titles and direct links
- **Robust Error Handling**: Comprehensive error handling and logging
- **Configurable**: Easy JSON-based configuration

## 📱 Sample Telegram Messages

When new jobs are posted, you'll receive messages like:

```
🚨 CHANGE DETECTED
⏰ 2024-01-15 14:30:25

🆕 New Jobs: Goldman Sachs Jobs

📝 Goldman Sachs - Data Analytics, Reporting & Software Engineering Jobs

🔗 View All Jobs

📊 Current Status:
• Total Jobs: 62
• Jobs Tracked: 20

📝 New Job Postings:
🆕 New Jobs Found: 3

1. Software Engineer - Machine Learning
2. Data Analyst - Associate
3. Backend Developer - Analyst

📊 Total Jobs: 59 → 62
```

## 📁 Project Structure

```
website_tracker/
├── tracker.py              # Main job posting tracker
├── config.json             # Job board configuration
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── data/                   # Auto-generated data files
│   ├── Website_Name_hash.txt
│   └── Website_Name_data.json
└── README.md               # This file
```

## ⚙️ Configuration

### 1. Pre-configured Job Boards

Your `config.json` already includes 5 major job boards:

- **Goldman Sachs Jobs** - Data Analytics, Reporting & Software Engineering
- **Barclays Jobs** - United States listings
- **Microsoft Careers** - Software Engineering, Research, Applied & Data Sciences
- **Apple Jobs** - ML/AI, Software Engineering, DevOps, Security & Analytics
- **PayPal Careers** - Software Engineering, Data Science & ML Engineering

### 2. Environment Variables

Create a `.env` file in the project root:

```bash
TELEGRAM_BOT_TOKEN=7623240757:AAHiPQ8QuwZN8SYRvtCV14RwvF04nCTwP3E
TELEGRAM_CHAT_ID=your_chat_id_here
CHECK_INTERVAL=600
```

### 3. Website Configuration Options

Each job board in `config.json` can have:
- **`name`** (required): Display name for the job board
- **`url`** (required): URL to monitor (filtered job search page)
- **`enabled`** (optional): Enable/disable monitoring (default: `true`)
- **`check_interval`** (optional): Check interval in seconds (default: 600 = 10 minutes)
- **`description`** (optional): Description shown in notifications

## 🔧 Setup Instructions

### 1. Telegram Bot (Already Created!)

Your bot is already created: [@gs_tracker_bot](https://t.me/gs_tracker_bot)

**Bot Token:** `7623240757:AAHiPQ8QuwZN8SYRvtCV14RwvF04nCTwP3E`

### 2. Get Your Chat ID

1. **Message your bot** on Telegram: [@gs_tracker_bot](https://t.me/gs_tracker_bot)
2. **Visit this URL**:
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

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Tracker

```bash
python tracker.py
```

The tracker will:
- Load job boards from `config.json`
- Monitor all enabled job boards simultaneously
- Extract job postings using website-specific patterns
- Send Telegram notifications when new jobs are detected
- Store tracking data in `data/` directory

## 🎯 How It Works

### Job Detection

The tracker uses website-specific URL patterns to accurately detect job postings:

- **Goldman Sachs**: Detects links containing `/roles/` or `/roles`
- **Apple**: Detects links containing `/details/` or `/details`
- **Barclays, Microsoft, PayPal**: Detects links containing `/job` or `/jobs`

### Change Detection

1. **Hash Comparison**: Compares page content hash to detect changes
2. **Job Extraction**: Extracts job titles and URLs from the page
3. **Job Comparison**: Compares current jobs with previous check
4. **Smart Filtering**: Only alerts when new jobs are actually posted
5. **Notification**: Sends Telegram message with new job details

### False Positive Prevention

- Filters out dynamic content (timestamps, session IDs, ads)
- Only alerts on meaningful job changes
- Ignores minor page updates
- Validates job links match expected patterns

## 📊 What Gets Tracked

- **New Job Postings**: Detects when new jobs are added
- **Job Count Changes**: Tracks total number of jobs
- **Job Titles**: Extracts and compares job titles
- **Job URLs**: Captures direct links to job postings
- **Page Updates**: Monitors for significant changes

## ⏱️ Check Intervals

Default check interval: **10 minutes (600 seconds)**

You can customize the interval for each job board in `config.json`:

```json
{
  "name": "Goldman Sachs Jobs",
  "check_interval": 300,  // 5 minutes
  ...
}
```

Common intervals:
- `60` = 1 minute (very frequent)
- `300` = 5 minutes
- `600` = 10 minutes (default)
- `1800` = 30 minutes
- `3600` = 1 hour

## 🔍 Troubleshooting

### Common Issues:

1. **ChromeDriver Errors**: 
   - Install ChromeDriver: `brew install chromedriver`
   - The tracker will automatically fall back to system ChromeDriver

2. **No Jobs Detected**:
   - Check that the URL in `config.json` is correct
   - Verify the job board page loads correctly
   - Check console logs for extraction errors

3. **Telegram Notifications Not Working**:
   - Verify bot token and chat ID in `.env` file
   - Make sure you've messaged the bot first
   - Check Telegram API status

4. **False Alerts**:
   - The tracker filters dynamic content automatically
   - If you still get false alerts, the hash cleaning may need adjustment

5. **Config Errors**:
   - Verify `config.json` is valid JSON
   - Check that all required fields are present

## 📈 Monitoring Multiple Job Boards

The tracker supports monitoring multiple job boards:

- **Parallel Monitoring**: Each job board runs in its own thread
- **Independent Intervals**: Each job board can have its own check interval
- **Separate Data Files**: Each job board has its own hash and data files
- **Isolated Errors**: Errors for one job board don't affect others

## 🛡️ Error Handling

- **Network Issues**: Automatic retry and error reporting
- **Page Changes**: Adapts to website structure changes
- **Telegram Failures**: Detailed error logging
- **Chrome Driver**: Multiple fallback methods for driver setup
- **Per-Job Board Errors**: Errors for one job board don't affect others

## 📝 Adding New Job Boards

To add a new job board, edit `config.json`:

```json
{
  "websites": [
    {
      "name": "New Job Board",
      "url": "https://jobs.example.com/search?...",
      "enabled": true,
      "check_interval": 600,
      "description": "Description of the job board"
    }
  ]
}
```

The tracker will automatically detect the URL pattern:
- If URL contains `/roles` → Uses GS pattern
- If URL contains `/details` → Uses Apple pattern
- Otherwise → Uses generic `/job` pattern

## 🚀 Performance Tips

- **Check Intervals**: Longer intervals (10+ minutes) reduce server load
- **Multiple Job Boards**: Each runs independently, so adding more doesn't slow down others
- **Data Storage**: Old data files are automatically managed
- **Resource Usage**: Uses headless Chrome, minimal resource footprint

## 📝 License

MIT License - Feel free to modify and use for your own projects!

---

**Happy Job Hunting! 🎯**
