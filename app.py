#!/usr/bin/env python3
"""
Web service wrapper for GS Job Tracker
This allows the tracker to run on Render's free tier as a web service
"""

import os
import threading
import time
from flask import Flask, jsonify
from datetime import datetime

# Import the tracker functions
from tracker import check_for_changes, send_telegram_alert, load_env_file

# Load environment variables
load_env_file()

app = Flask(__name__)

# Global variables to track status
tracker_status = {
    'running': False,
    'last_check': None,
    'start_time': None,
    'checks_performed': 0,
    'errors': []
}

def run_tracker():
    """Background task to run the tracker"""
    global tracker_status
    
    tracker_status['running'] = True
    tracker_status['start_time'] = datetime.now().isoformat()
    
    print("🚀 Starting GS Job Tracker in background...")
    
    # Send startup message
    try:
        send_telegram_alert("🚀 <b>GS Job Tracker Started</b>\n\nMonitoring for new job postings on Render...")
    except Exception as e:
        print(f"[-] Error sending startup message: {e}")
    
    while tracker_status['running']:
        try:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running background check...")
            check_for_changes()
            tracker_status['last_check'] = datetime.now().isoformat()
            tracker_status['checks_performed'] += 1
            
            # Wait for next check (10 minutes)
            time.sleep(600)
            
        except Exception as e:
            error_msg = f"Background tracker error: {str(e)}"
            print(f"[-] {error_msg}")
            tracker_status['errors'].append({
                'time': datetime.now().isoformat(),
                'error': str(e)
            })
            
            # Wait a bit before retrying
            time.sleep(60)

@app.route('/')
def home():
    """Home page showing tracker status"""
    return jsonify({
        'status': 'running',
        'service': 'GS Job Tracker',
        'tracker_status': tracker_status,
        'message': 'Tracker is running in background. Check Telegram for notifications.'
    })

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'tracker_running': tracker_status['running']
    })

@app.route('/status')
def status():
    """Detailed status endpoint"""
    return jsonify({
        'service': 'GS Job Tracker',
        'tracker_status': tracker_status,
        'environment': 'Render Web Service',
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