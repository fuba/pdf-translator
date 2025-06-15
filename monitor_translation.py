#!/usr/bin/env python3
"""Monitor translation progress and detect hanging processes."""

import subprocess
import time
import sys
from pathlib import Path

def monitor_translation(pdf_path: str, timeout_per_page: int = 600):
    """Monitor translation progress and provide status updates."""
    
    print(f"🚀 Starting translation monitoring for: {pdf_path}")
    print(f"⏰ Timeout per page: {timeout_per_page}s")
    print("-" * 50)
    
    # Start translation process
    cmd = [
        "./run-uv.sh", "run", "python", "main.py", 
        pdf_path, 
        "--engine", "ollama", 
        "--format", "markdown", 
        "--target-lang", "ja",
        "-v"
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        last_activity = time.time()
        page_start_time = time.time()
        current_page = 0
        total_pages = None
        
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip())
                last_activity = time.time()
                
                # Parse progress information
                if "Processing page" in line and "/" in line:
                    try:
                        # Extract page info: "Processing page 2/10"
                        parts = line.split("Processing page")[1].strip()
                        page_info = parts.split()[0]  # "2/10"
                        current_page, total_pages = map(int, page_info.split("/"))
                        page_start_time = time.time()
                        print(f"📊 Page {current_page}/{total_pages} started")
                    except:
                        pass
                
                elif "completed in" in line:
                    page_duration = time.time() - page_start_time
                    if total_pages:
                        remaining = total_pages - current_page
                        estimated_remaining = remaining * page_duration
                        print(f"⏱️  Estimated remaining time: {estimated_remaining/60:.1f} minutes")
            
            # Check for timeout
            time_since_activity = time.time() - last_activity
            if time_since_activity > timeout_per_page:
                print(f"⚠️  WARNING: No activity for {time_since_activity:.1f}s")
                print(f"🛑 Process appears to be hanging. Terminating...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return False
        
        # Wait for process completion
        return_code = process.wait()
        
        if return_code == 0:
            print("✅ Translation completed successfully!")
            return True
        else:
            print(f"❌ Translation failed with return code: {return_code}")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Translation interrupted by user")
        if 'process' in locals():
            process.terminate()
        return False
    except Exception as e:
        print(f"❌ Error during translation: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python monitor_translation.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    success = monitor_translation(pdf_path)
    sys.exit(0 if success else 1)