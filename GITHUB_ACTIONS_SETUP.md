# 🚀 Free 24/7 Deployment Guide - GitHub Actions

Run your Microsoft Jobs Tracker **completely FREE** in the cloud using GitHub Actions!

## ✨ Why GitHub Actions?
- ✅ **100% Free** - No credit card required
- ✅ **24/7 Monitoring** - Runs in the cloud automatically
- ✅ **Easy Setup** - Just push to GitHub
- ✅ **Scheduled Runs** - Check every 5 minutes automatically

## 📋 Quick Setup (5 Minutes)

### Step 1: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in (create account if needed)
2. Click **"New Repository"** (green button)
3. Name it: `microsoft-jobs-tracker` (or any name)
4. Choose **Public** (required for unlimited free Actions)
5. Click **"Create repository"**

### Step 2: Add Your Telegram Credentials

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add these two secrets:

   **Secret 1:**
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: `8392210893:AAEYc5GMZ4iKYT8QcR0MCtEd-pDGbAzyCFU`
   
   **Secret 2:**
   - Name: `TELEGRAM_CHAT_ID`
   - Value: `957514980`

### Step 3: Upload Files to GitHub

#### Option A: Using GitHub Web Interface (Easiest)

1. In your repository, click **"Add file"** → **"Upload files"**
2. Upload these files from your local folder (`/Users/tejashiremath/Documents/website_tracker/`):
   - `tracker.py`
   - `run_once.py`
   - `config.json`
   - `filters.py`
   - `oracle_hcm_extractor.py`
   - `requirements.txt`
   - `.github/workflows/tracker.yml` (create folder structure if needed)
3. Click **"Commit changes"**

#### Option B: Using Git Command Line

```bash
cd /Users/tejashiremath/Documents/website_tracker

# Initialize git (if not already done)
git init

# Add remote (replace YOUR_USERNAME and YOUR_REPO with your GitHub info)
git remote add origin https://github.com/YOUR_USERNAME/microsoft-jobs-tracker.git

# Add all files
git add tracker.py run_once.py config.json filters.py oracle_hcm_extractor.py requirements.txt
git add .github/workflows/tracker.yml

# Commit
git commit -m "Initial commit - Microsoft Jobs Tracker"

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 4: Enable GitHub Actions

1. Go to your repository on GitHub
2. Click the **"Actions"** tab
3. If you see a prompt to enable workflows, click **"I understand my workflows, go ahead and enable them"**
4. You should see your workflow: "Microsoft Jobs Tracker"

### Step 5: Test It!

1. In the **Actions** tab, click on "Microsoft Jobs Tracker"
2. Click **"Run workflow"** → **"Run workflow"** (green button)
3. Wait 1-2 minutes
4. Check your Telegram - you should get notifications! 📱

## 🎯 How It Works

- **Automatic Runs**: GitHub Actions runs the tracker every **5 minutes** automatically
- **Free Minutes**: You get **2,000 free minutes/month** (way more than enough!)
- **Notifications**: Get instant Telegram alerts when Microsoft posts new jobs
- **Data Persistence**: Job data is stored as GitHub artifacts for 7 days

## ⚙️ Customization

### Change Check Frequency

Edit [`.github/workflows/tracker.yml`](.github/workflows/tracker.yml):

```yaml
schedule:
  # Every 5 minutes
  - cron: '*/5 * * * *'
  
  # Every 10 minutes
  - cron: '*/10 * * * *'
  
  # Every hour
  - cron: '0 * * * *'
  
  # Every 30 minutes
  - cron: '*/30 * * * *'
```

### Enable/Disable Job Boards

Edit [`config.json`](config.json) and set `"enabled": false` for boards you don't want to track:

```json
{
  "name": "Microsoft Careers",
  "enabled": true,  // Change to false to disable
  ...
}
```

### Track Only Microsoft

Edit [`config.json`](config.json) and disable all other boards except Microsoft.

## 📊 Monitoring

### View Workflow Runs

1. Go to **Actions** tab
2. Click on any workflow run to see details
3. Click on "track-jobs" to see logs

### Download Job Data

1. Go to a completed workflow run
2. Scroll to **Artifacts**
3. Download `job-data` to see detected jobs

## 🐛 Troubleshooting

### No Telegram notifications?

1. Check that secrets are set correctly in Settings → Secrets
2. Make sure your bot token and chat ID are correct
3. View workflow logs for errors

### Workflow not running automatically?

1. Make sure repository is **Public**
2. Check that workflow file is in `.github/workflows/`
3. Verify cron syntax is correct

### Getting rate limited?

- GitHub Actions has generous limits for public repos
- If needed, increase check interval to every 10-15 minutes

## 💰 Cost

**100% FREE** for public repositories with up to 2,000 minutes/month!

Running every 5 minutes = ~1 minute per run = ~300 runs/month = ~300 minutes/month

You're well within the free tier! 🎉

## 🔒 Security Notes

- Your Telegram bot token and chat ID are stored as encrypted secrets
- Only you can see them in your repository settings
- They're never exposed in logs or code

## 📞 Support

If you have issues:
1. Check the workflow logs in Actions tab
2. Verify your secrets are set correctly
3. Make sure all files are uploaded properly

## 🎉 You're All Set!

Once set up, you'll get notifications whenever Microsoft posts new jobs - all running for free in the cloud! 

**Stop your local tracker** (press Ctrl+C in the terminal) and let GitHub Actions handle it! 🚀
