#!/usr/bin/env python3
"""
Check training status and logs
"""

import requests
import json
import time

def check_training_status(session_id):
    """Check the status of a training session"""
    try:
        response = requests.get(f"http://localhost:8001/api/fine-tuning/status/{session_id}")
        if response.status_code == 200:
            status = response.json()
            print(f"📊 Training Status for {session_id}:")
            print(f"   Status: {status.get('status')}")
            print(f"   Progress: {status.get('progress', 0):.1f}%")
            print(f"   Current Epoch: {status.get('current_epoch')}/{status.get('total_epochs')}")
            print(f"   Train Loss: {status.get('train_loss', 0):.4f}")
            print(f"   Learning Rate: {status.get('learning_rate', 0):.6f}")
            print(f"   Message: {status.get('message')}")
            
            if status.get('error'):
                print(f"   ❌ Error: {status.get('error')}")
                
            return status
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return None

def monitor_training(session_id, duration_minutes=10):
    """Monitor training for a specified duration"""
    print(f"🔍 Monitoring training session: {session_id}")
    print(f"⏱️  Will monitor for {duration_minutes} minutes")
    print("=" * 50)
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    while time.time() < end_time:
        status = check_training_status(session_id)
        if status:
            if status.get('status') in ['completed', 'failed', 'stopped']:
                print(f"🏁 Training finished with status: {status.get('status')}")
                break
        
        time.sleep(5)  # Check every 5 seconds
        print("-" * 30)

def list_all_sessions():
    """List all training sessions"""
    try:
        # This would need to be implemented in the backend
        # For now, we'll just show how to check a specific session
        print("📋 To check a specific session, use:")
        print("   python check_training_status.py <session_id>")
        print("")
        print("💡 You can find session IDs in the frontend or backend logs")
    except Exception as e:
        print(f"Error: {e}")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("🔍 Training Status Checker")
        print("=" * 30)
        print("Usage:")
        print("  python check_training_status.py <session_id>")
        print("  python check_training_status.py <session_id> --monitor [minutes]")
        print("")
        print("Examples:")
        print("  python check_training_status.py training_1758028022")
        print("  python check_training_status.py training_1758028022 --monitor 10")
        print("")
        list_all_sessions()
        return
    
    session_id = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == "--monitor":
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        monitor_training(session_id, duration)
    else:
        check_training_status(session_id)

if __name__ == "__main__":
    main()
