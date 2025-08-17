#!/usr/bin/env python3
"""
QR Code Utilities Module
Provides functions for reading QR codes from images and screenshots
"""

import subprocess
import urllib.request
import urllib.parse
import urllib.error
import json
import tempfile
import os
import sys
import time
from pathlib import Path
from typing import Optional, Union


def copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS clipboard using pbcopy"""
    try:
        process = subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error copying to clipboard: {e}")
        return False
    except FileNotFoundError:
        print("pbcopy command not found. This function is macOS-specific.")
        return False


def show_alert(title: str, message: str) -> bool:
    """Show a macOS alert dialog"""
    try:
        subprocess.run([
            'osascript', '-e', 
            f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"'
        ], check=True)
        return True
    except subprocess.CalledProcessError:
        # If alert fails, just print to console
        print(f"{title}: {message}")
        return False
    except FileNotFoundError:
        print(f"{title}: {message}")
        return False


def focus_signal_app() -> bool:
    """Focus the Signal Desktop app"""
    try:
        subprocess.run([
            'osascript', '-e', 
            'tell application "Signal" to activate'
        ], check=True)
        return True
    except subprocess.CalledProcessError:
        # If Signal app not found or can't be focused, just continue
        print("Note: Could not focus Signal app (may not be running)")
        return False
    except FileNotFoundError:
        print("Note: Could not focus Signal app")
        return False


def take_interactive_screenshot(debug: bool = False, attempt: int = 1) -> Optional[str]:
    """Take an interactive screenshot using macOS screencapture"""
    timestamp = int(time.time())
    screenshot_file = f"qr_screenshot_{timestamp}.png"
    
    try:
        # Show alert before screenshot selector
        alert_message = "After you press 'OK' you will get a selector that you should draw a square on top of the QR code in Signal Desktop"
        if attempt > 1:
            alert_message += f"\\n\\nAttempt #{attempt} of 3"
        show_alert("QR Code Screenshot", alert_message)
        
        print("📸 Taking screenshot... Select the QR code area")
        
        # Focus Signal app
        focus_signal_app()
        
        # Try screencapture first
        result = subprocess.run(['screencapture', '-i', screenshot_file], check=True)
        
        # Check if file was actually created (user might have cancelled)
        if os.path.exists(screenshot_file) and os.path.getsize(screenshot_file) > 0:
            if debug:
                file_size = os.path.getsize(screenshot_file)
                print(f"📸 Screenshot saved to: {screenshot_file}")
                print(f"📊 File size: {file_size} bytes")
                
                # Check if the screenshot might be just desktop background
                if file_size < 10000:  # Very small file might indicate failure
                    print("⚠️  Warning: Screenshot file is very small, may not have captured properly")
                    print("   Try granting Screen Recording permission to Terminal/Python")
            
            return screenshot_file
        else:
            print("Screenshot cancelled by user or failed")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Error taking screenshot: {e}")
        return None
    except FileNotFoundError:
        print("screencapture command not found. This function is macOS-specific.")
        return None



def read_qr_code_from_image(image_path: Union[str, Path]) -> Optional[str]:
    """Send image to QR code reading API and extract data using built-in urllib"""
    try:
        # Prepare the multipart form data manually
        boundary = '----WebKitFormBoundary' + ''.join([str(x) for x in range(10)])
        
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        
        # Build multipart form data with proper line endings
        form_data = []
        form_data.append(f'--{boundary}\r\n'.encode())
        form_data.append(b'Content-Disposition: form-data; name="file"; filename="image.png"\r\n')
        form_data.append(b'Content-Type: image/png\r\n')
        form_data.append(b'\r\n')
        form_data.append(image_data)
        form_data.append(b'\r\n')
        form_data.append(f'--{boundary}--\r\n'.encode())
        
        body = b''.join(form_data)
        
        # Create request
        url = 'http://api.qrserver.com/v1/read-qr-code/'
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body))
        }
        
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        
        print(f"Making API request to: {url}")
        print(f"Image size: {len(image_data)} bytes")
        print(f"Request body size: {len(body)} bytes")
        
        # Make the request
        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"API response status: {response.status}")
            if response.status == 200:
                response_data = response.read().decode('utf-8')
                print(f"API response length: {len(response_data)} characters")
                
                data = json.loads(response_data)
                
                # Extract QR code data from response
                if data and len(data) > 0:
                    # The API returns an array, first item contains the symbols
                    first_item = data[0]
                    if 'symbol' in first_item and first_item['symbol']:
                        # symbols is an array, get the first symbol's data
                        first_symbol = first_item['symbol'][0]
                        if 'data' in first_symbol and first_symbol['data']:
                            return first_symbol['data']
                
                print("No QR code data found in image")
                return None
            else:
                print(f"API request failed with status code: {response.status}")
                return None
                
    except urllib.error.URLError as e:
        print(f"Network error: {e}")
        return None
    except urllib.error.HTTPError as e:
        print(f"HTTP error: {e.code} - {e.reason}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing API response: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error reading QR code: {e}")
        return None


def read_qr_code_from_image_alternative(image_path: Union[str, Path]) -> Optional[str]:
    """Alternative method using a different API endpoint"""
    try:
        print("Trying alternative QR code reading method...")
        
        # Try using the GoQR.me API instead
        url = 'https://api.qrcode-monkey.com/qr/custom'
        
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        
        # Convert to base64
        import base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Try a simpler approach - just send the image directly
        print("Trying direct image upload...")
        
        # Use the original API but with a different approach
        url = 'https://api.qrserver.com/v1/read-qr-code/'
        
        # Create a simpler multipart form
        boundary = '----WebKitFormBoundary' + ''.join([str(x) for x in range(10)])
        
        # Build multipart form data
        form_data = []
        form_data.append(f'--{boundary}\r\n'.encode())
        form_data.append(b'Content-Disposition: form-data; name="file"; filename="screenshot.png"\r\n')
        form_data.append(b'Content-Type: image/png\r\n')
        form_data.append(b'\r\n')
        form_data.append(image_data)
        form_data.append(b'\r\n')
        form_data.append(f'--{boundary}--\r\n'.encode())
        
        body = b''.join(form_data)
        
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                response_data = response.read().decode('utf-8')
                
                data = json.loads(response_data)
                
                if data and len(data) > 0:
                    # The API returns an array, first item contains the symbols
                    first_item = data[0]
                    if 'symbol' in first_item and first_item['symbol']:
                        # symbols is an array, get the first symbol's data
                        first_symbol = first_item['symbol'][0]
                        if 'data' in first_symbol and first_symbol['data']:
                            return first_symbol['data']
                
                print("Alternative method also failed")
                return None
            else:
                print(f"Alternative method failed with status: {response.status}")
                return None
                
    except Exception as e:
        print(f"Alternative method error: {e}")
        return None


def read_qr_code_from_file(file_path: Union[str, Path]) -> Optional[str]:
    """Read QR code from an existing image file"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None
    
    return read_qr_code_from_image(file_path)


def show_notification(title: str, message: str) -> bool:
    """Show a macOS notification"""
    try:
        subprocess.run([
            'osascript', '-e', 
            f'display notification "{message}" with title "{title}"'
        ], check=True)
        return True
    except subprocess.CalledProcessError:
        # If notification fails, just print to console
        print(f"{title}: {message}")
        return False
    except FileNotFoundError:
        print(f"{title}: {message}")
        return False


def show_terminal_permission_error():
    """Show terminal permission error and instructions, then exit"""
    print("\n" + "="*60)
    print("⚠️⚠️⚠️  TERMINAL PERMISSION REQUIRED  ⚠️⚠️⚠️")
    print("="*60)
    print()
    print("Your terminal app needs permission to take screenshots.")
    print("This is required for automatic QR code reading.")
    print()
    print("INSTRUCTIONS:")
    print("1. Go to System Preferences > Security & Privacy > Privacy")
    print("2. Select 'Screen Recording' from the left sidebar")
    print("3. Click the lock icon to make changes (enter your password)")
    print("4. Find your terminal app (Terminal, iTerm2, etc.) in the list")
    print("5. Check the box next to it to grant permission")
    print("6. Restart your terminal app completely")
    print("7. Run this script again")
    print()
    print("Note: You may need to restart your terminal app for changes to take effect.")
    print("="*60)
    print("\nExiting due to terminal permission requirements.")
    print("Please restart your terminal and run this script again after granting permissions.")
    sys.exit(1)


def copy_qr_code_from_screenshot(debug: bool = False) -> Optional[str]:
    """
    Take a screenshot, read QR code, and return the data.
    Returns the QR code data if successful, None otherwise.
    """
    max_attempts = 3
    screenshot_failures = 0  # Track screenshot failures separately
    
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            print(f"🔄 Retry attempt {attempt}/{max_attempts}...")
        
        # Step 1: Take screenshot
        screenshot_path = take_interactive_screenshot(debug, attempt)
        if not screenshot_path:
            
            # Continue with normal retry logic
            if attempt < max_attempts:
                print("Will retry...")
                continue
            else:
                # After all attempts, show final permission error
                print("❌ All screenshot attempts failed after 3 retries")
                print("This is likely due to missing screen recording permissions.")
                show_terminal_permission_error()
                # show_terminal_permission_error() calls sys.exit(1)
        
        try:
            if debug:
                print("Reading QR code...")
            
            # Step 2: Read QR code from screenshot
            qr_data = read_qr_code_from_image(screenshot_path)
            
            if qr_data:
                print(f"✅ QR code found: {qr_data}")
                return qr_data
            else:
                print("❌ No QR code found in screenshot")
                
                # Handle warning on first QR code reading failure
                if attempt == 1:  # First attempt failure
                    print("\n🚨 WARNING: QR code reading failed!")
                    print("This is likely due to missing terminal screen recording permissions.")
                    
                    # Show dialog asking if they've given permissions
                    try:
                        result = subprocess.run([
                            'osascript', '-e', 
                            'display dialog "🚨 QR code reading failed!\n\nHave you given your terminal screen recording permissions in System Preferences > Security & Privacy > Privacy > Screen Recording?\n\nClick Yes if you have, No if you need instructions." buttons {"I need instructions", "Yes, I gave permissions"} default button "I need instructions"'
                        ], capture_output=True, text=True, check=True)
                        
                        if "Yes" in result.stdout:
                            print("✅ User confirmed permissions are granted. Retrying...")
                            if attempt < max_attempts:
                                print("Will retry...")
                                continue
                            else:
                                print("❌ Maximum attempts reached")
                                return None
                        else:
                            print("ℹ️ User needs permission instructions.")
                            show_terminal_permission_error()
                            # show_terminal_permission_error() calls sys.exit(1)
                    except Exception as e:
                        print(f"⚠️  Could not show retry dialog: {e}")
                        print("Continuing with normal retry logic...")
                
                if attempt < max_attempts:
                    print("Will retry...")
                    continue
                else:
                    # After all attempts, return None to indicate QR reading failure
                    print("❌ Failed to read QR code from screenshot after 3 attempts")
                    return None
                
        finally:
            # Only keep screenshot file if debug mode is enabled
            if debug:
                print(f"💾 Screenshot file kept at: {screenshot_path}")
                print("   You can manually delete it when done, or it will be overwritten on next run")
            else:
                # Clean up screenshot file in normal mode
                try:
                    os.remove(screenshot_path)
                except:
                    pass  # Ignore cleanup errors
    
    # This should never be reached
    return None


def copy_qr_code_to_clipboard(qr_data: str) -> bool:
    """Copy QR code data to clipboard and show notification"""
    if copy_to_clipboard(qr_data):
        print(f"✅ Copied to clipboard: {qr_data}")
        show_notification("QR Code Reader", f"Copied: {qr_data[:50]}{'...' if len(qr_data) > 50 else ''}")
        return True
    else:
        print("❌ Failed to copy to clipboard")
        return False


def is_macos() -> bool:
    """Check if running on macOS"""
    return sys.platform == "darwin"


def check_dependencies() -> bool:
    """Check if required system commands are available"""
    if not is_macos():
        print("This module is designed for macOS only")
        return False
    
    required_commands = ['screencapture', 'pbcopy']
    missing_commands = []
    
    for cmd in required_commands:
        if subprocess.run(['which', cmd], capture_output=True).returncode != 0:
            missing_commands.append(cmd)
    
    if missing_commands:
        print(f"Missing required commands: {', '.join(missing_commands)}")
        return False
    
    return True


# Convenience function that combines screenshot + clipboard copy
def screenshot_and_copy_qr(debug: bool = False) -> bool:
    """
    Complete workflow: take screenshot, read QR code, copy to clipboard.
    Returns True if successful, False otherwise.
    """
    qr_data = copy_qr_code_from_screenshot(debug)
    if qr_data:
        return copy_qr_code_to_clipboard(qr_data)
    return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="QR Code Reader - Take screenshot and copy QR code to clipboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (no debug)
  python3 qr_utils.py
  
  # Enable debug mode (keeps screenshot files)
  python3 qr_utils.py --debug
        """
    )
    
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode (keeps screenshot files and shows detailed output)')
    
    args = parser.parse_args()
    
    # Demo/test functionality when run directly
    if not check_dependencies():
        sys.exit(1)
    
    print("=== QR Code Reader ===")
    print("Taking screenshot and copying QR code to clipboard...")
    
    success = screenshot_and_copy_qr(debug=args.debug)
    if success:
        print("Successfully copied QR code to clipboard!")
    else:
        print("Failed to process QR code")
        sys.exit(1)
