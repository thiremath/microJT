#!/usr/bin/env python3
"""
Web service wrapper for Generic Website Tracker
This allows the tracker to run on Render's free tier as a web service
"""

import os
import threading
import time
from flask import Flask, jsonify
from datetime import datetime

# Import the tracker functions
from tracker import CONFIG, monitor_website, send_telegram_alert

app = Flask(__name__)

# Global variables to track status
tracker_status = {
    'running': False,
    'last_check': None,
    'start_time': None,
    'checks_performed': 0,
    'errors': [],
    'websites': []
}

def run_tracker():
    """Background task to run the tracker"""
    global tracker_status
    
    tracker_status['running'] = True
    tracker_status['start_time'] = datetime.now().isoformat()
    
    print("🚀 Starting Generic Website Tracker in background...")
    
    # Get enabled websites
    websites = [w for w in CONFIG.get('websites', []) if w.get('enabled', True)]
    tracker_status['websites'] = [w['name'] for w in websites]
    
    # Send startup message
    try:
        website_list = "\n".join([f"• {w['name']}" for w in websites])
        send_telegram_alert(
            f"🚀 <b>Website Tracker Started</b>\n\n"
            f"📊 Monitoring {len(websites)} website(s) on Render:\n{website_list}"
        )
    except Exception as e:
        print(f"[-] Error sending startup message: {e}")
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Monitor all websites
    if len(websites) == 1:
        # Single website - simple loop
        monitor_website(websites[0])
    else:
        # Multiple websites - use threads
        threads = []
        for website in websites:
            thread = threading.Thread(target=monitor_website, args=(website,), daemon=True)
            thread.start()
            threads.append(thread)
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n[!] Stopping tracker...")

@app.route('/')
def home():
    """Home page showing tracker status"""
    return jsonify({
        'status': 'running',
        'service': 'Generic Website Tracker',
        'tracker_status': tracker_status,
        'message': 'Tracker is running in background. Check Telegram for notifications.',
        'websites': tracker_status.get('websites', [])
    })

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'tracker_running': tracker_status['running'],
        'websites_monitored': len(tracker_status.get('websites', []))
    })

@app.route('/status')
def status():
    """Detailed status endpoint"""
    return jsonify({
        'service': 'Generic Website Tracker',
        'tracker_status': tracker_status,
        'environment': 'Render Web Service',
        'websites': tracker_status.get('websites', []),
        'uptime': datetime.now().isoformat() if tracker_status['start_time'] else None
    })

if __name__ == '__main__':
    # Start the background tracker in a separate thread
    tracker_thread = threading.Thread(target=run_tracker, daemon=True)
    tracker_thread.start()
    
    print("🌐 Starting web service on port 10000...")
    print("📊 Tracker status available at: /status")
    print("🏥 Health check available at: /health")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=10000, debug=False)
 