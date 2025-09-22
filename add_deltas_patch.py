#!/usr/bin/env python3
"""
Add view deltas functionality to the optimized monitor
"""

# Read the current file
with open('simple_multi_monitor_optimized.py', 'r') as f:
    content = f.read()

# Add json import
content = content.replace(
    'import csv',
    'import csv\nimport json'
)

# Add the save_view_deltas function
save_deltas_function = '''
def save_view_deltas(username, current_videos, previous_videos):
    """Save view deltas to CSV and JSON files."""
    try:
        # Create lookup for previous videos
        prev_lookup = {v['video_id']: v for v in previous_videos}
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        # Prepare delta data
        deltas = []
        timestamp = datetime.now().isoformat()
        
        for current_video in current_videos:
            video_id = current_video.get('video_id')
            if not video_id:
                continue
                
            current_views = current_video.get('views', 0)
            previous_video = prev_lookup.get(video_id)
            previous_views = previous_video.get('views', 0) if previous_video else 0
            delta = current_views - previous_views
            
            delta_data = {
                'timestamp': timestamp,
                'username': username,
                'video_id': video_id,
                'previous_views': previous_views,
                'current_views': current_views,
                'delta': delta
            }
            deltas.append(delta_data)
            
            # Write to JSON file (append)
            try:
                with open('data/view_deltas.jsonl', 'a') as f:
                    json.dump(delta_data, f)
                    f.write('\\n')
            except Exception as e:
                logging.error(f"Error writing to JSON: {e}")
            
            # Write to CSV file (append)
            try:
                file_exists = os.path.exists('data/view_deltas.csv')
                with open('data/view_deltas.csv', 'a', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['timestamp', 'username', 'video_id', 'previous_views', 'current_views', 'delta'])
                    writer.writerow([timestamp, username, video_id, previous_views, current_views, delta])
            except Exception as e:
                logging.error(f"Error writing to CSV: {e}")
        
        logging.info(f"📊 Saved {len(deltas)} view deltas for @{username}")
        
    except Exception as e:
        logging.error(f"Error saving view deltas for {username}: {e}")

'''

# Insert the function before the check_viral_videos function
content = content.replace(
    'def check_viral_videos(username, current_videos, previous_videos):',
    save_deltas_function + '\ndef check_viral_videos(username, current_videos, previous_videos):'
)

# Modify the viral check function to call save_view_deltas
old_viral_check = '''def check_viral_videos(username, current_videos, previous_videos):
    """Check for viral videos by comparing current and previous data."""
    viral_videos = []
    
    # Create lookup for previous videos
    prev_lookup = {v['video_id']: v for v in previous_videos}'''

new_viral_check = '''def check_viral_videos(username, current_videos, previous_videos):
    """Check for viral videos by comparing current and previous data."""
    
    # Save view deltas to files
    save_view_deltas(username, current_videos, previous_videos)
    
    viral_videos = []
    
    # Create lookup for previous videos
    prev_lookup = {v['video_id']: v for v in previous_videos}'''

content = content.replace(old_viral_check, new_viral_check)

# Write the patched file
with open('simple_multi_monitor_optimized.py', 'w') as f:
    f.write(content)

print("✅ Successfully added view deltas functionality!")
print("The monitor will now save view deltas to:")
print("  - data/view_deltas.csv")
print("  - data/view_deltas.jsonl")
