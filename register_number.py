#!/usr/bin/env python3
"""
Signal CLI Registration Script
Supports both new account registration and linking as secondary device
"""

import argparse
import subprocess
import sys
import time
from typing import Optional
import os

# Import QR utilities
try:
    import qr_utils
    QR_UTILS_AVAILABLE = True
except ImportError:
    QR_UTILS_AVAILABLE = False
    print("Note: qr_utils.py not found. Manual URI input will be required for device linking.")


class SignalCLIRegistration:
    def __init__(self):
        self.phone_number = None
        self.device_name = "signal-cli-desktop"
        self.captcha_url = "https://signalcaptchas.org/registration/generate.html"
        
    def check_signal_cli(self) -> bool:
        """Check if signal-cli is installed and accessible"""
        try:
            result = subprocess.run(['signal-cli', '--version'], 
                                  capture_output=True, text=True, check=True)
            print("✓ signal-cli found")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: signal-cli is not installed or not in PATH")
            print("Please install signal-cli first:")
            print("  wget https://github.com/AsamK/signal-cli/releases/latest")
            return False
    
    def check_qr_utilities(self) -> bool:
        """Check if QR utilities are available and working"""
        if not QR_UTILS_AVAILABLE:
            print("⚠️  qr_utils.py not available - manual URI input will be required")
            return False
        
        try:
            # Check if qr_utils has the required dependencies
            if hasattr(qr_utils, 'check_dependencies'):
                if qr_utils.check_dependencies():
                    print("✓ QR utilities available and ready")
                    return True
                else:
                    print("⚠️  QR utilities available but system dependencies missing")
                    return False
            else:
                print("✓ QR utilities available")
                return True
        except Exception as e:
            print(f"⚠️  Error checking QR utilities: {e}")
            return False
    

    
    def get_captcha_token(self) -> str:
        """Get captcha token from user"""
        print("\n=== Captcha Token Required ===")
        print(f"1. Open this URL in your browser: {self.captcha_url}")
        print("2. Open Developer Tools (F12)")
        print("3. Go to Console tab")
        print("4. Solve the captcha")
        print("5. Look for a line like: 'Launched external handler for \"signalcaptcha://...\"'")
        print("6. Copy the entire line or just the token part")
        print()
        print("Note: If pasting the long token causes issues, try pasting it in smaller parts")
        print("or save it to a file and use: python3 register-number.py --captcha-file <filename>")
        print()
        
        while True:
            try:
                captcha_input = input("Enter captcha token or full line: ").strip()
                if not captcha_input:
                    print("Error: Captcha token cannot be empty")
                    continue
                
                # Extract token from the full line if provided
                captcha_token = self.extract_captcha_token(captcha_input)
                if captcha_token:
                    print("✓ Captcha token extracted successfully")
                    return captcha_token
                else:
                    print("Error: Could not extract captcha token from input")
                    print("Please provide either the full line or just the token part")
            except KeyboardInterrupt:
                print("\n\nInput interrupted. You can also:")
                print("1. Try pasting the token in smaller parts")
                print("2. Save the token to a file and use --captcha-file option")
                print("3. Run the script again")
                sys.exit(1)
            except Exception as e:
                print(f"Input error: {e}")
                print("Try pasting the token in smaller parts or use --captcha-file option")
                continue
    
    def extract_captcha_token(self, input_text: str) -> str:
        """Extract captcha token from various input formats"""
        # Remove quotes if present
        input_text = input_text.strip('"\'')
        
        # Look for signalcaptcha:// pattern
        if 'signalcaptcha://' in input_text:
            # Extract everything after signalcaptcha://
            token_start = input_text.find('signalcaptcha://') + len('signalcaptcha://')
            return input_text[token_start:]
        
        # If no signalcaptcha:// prefix, assume it's just the token
        if input_text and not input_text.startswith('signalcaptcha://'):
            return input_text
        
        return ""
    
    def read_captcha_from_file(self, filename: str) -> str:
        """Read captcha token from a file"""
        try:
            with open(filename, 'r') as f:
                content = f.read().strip()
            
            if not content:
                raise ValueError("File is empty")
            
            # Extract token from the content
            captcha_token = self.extract_captcha_token(content)
            if not captcha_token:
                raise ValueError("Could not extract captcha token from file content")
            
            return captcha_token
            
        except FileNotFoundError:
            raise ValueError(f"File '{filename}' not found")
        except PermissionError:
            raise ValueError(f"Permission denied reading file '{filename}'")
        except Exception as e:
            raise ValueError(f"Error reading file: {e}")
    
    def register_sms(self, captcha_token: str) -> bool:
        """Register with SMS verification"""
        print("\n=== Registering with SMS ===")
        try:
            subprocess.run([
                'signal-cli', '-a', self.phone_number, 'register',
                '--captcha', f"signalcaptcha://{captcha_token}"
            ], check=True)
            print("✓ Registration request sent via SMS")
            return True
        except subprocess.CalledProcessError:
            print("⚠ SMS registration failed, will try voice verification")
            return False
    
    def register_voice(self, captcha_token: str) -> bool:
        """Register with voice call verification"""
        print("\n=== Registering with Voice Call ===")
        print("Waiting 60 seconds before attempting voice verification...")
        time.sleep(60)
        
        try:
            subprocess.run([
                'signal-cli', '-a', self.phone_number, 'register',
                '--voice', '--captcha', f"signalcaptcha://{captcha_token}"
            ], check=True)
            print("✓ Voice call registration initiated")
            print("You should receive a call shortly with the verification code")
            return True
        except subprocess.CalledProcessError:
            print("Error: Voice registration failed")
            return False
    
    def verify_code(self) -> bool:
        """Verify the registration code"""
        print("\n=== Verification ===")
        
        while True:
            verification_code = input("Enter the 6-digit verification code you received: ").strip()
            if verification_code and len(verification_code) == 6 and verification_code.isdigit():
                break
            print("Error: Please enter a valid 6-digit verification code")
        
        has_pin = input("Do you have a registration PIN? (y/n): ").strip().lower()
        
        try:
            if has_pin in ['y', 'yes']:
                pin_code = input("Enter your PIN: ").strip()
                subprocess.run([
                    'signal-cli', '-a', self.phone_number, 'verify',
                    verification_code, '--pin', pin_code
                ], check=True)
                print("✓ Account verified successfully with PIN")
            else:
                subprocess.run([
                    'signal-cli', '-a', self.phone_number, 'verify', verification_code
                ], check=True)
                print("✓ Account verified successfully")
            return True
        except subprocess.CalledProcessError:
            print("Error: Verification failed")
            return False
    
    def test_registration(self) -> bool:
        """Test the registration by sending a test message"""
        print("\n=== Testing Registration ===")
        try:
            subprocess.run([
                'signal-cli', '-a', self.phone_number, 'send',
                '--note-to-self', '-m', 'Test message - Signal CLI registration successful!'
            ], check=True)
            print("✓ Test message sent successfully")
            print("Check your Signal app for the test message")
            return True
        except subprocess.CalledProcessError:
            print("⚠ Could not send test message, but registration may still be successful")
            return False
    

    
    
    def setup_daemon_info(self, is_primary: bool = True):
        """Provide daemon setup information"""
        if is_primary:
            print("\n=== Important: Regular Message Receiving ===")
            print("Signal protocol requires regular message receiving for proper encryption.")
            print("You should regularly run:")
            print(f"  signal-cli -a {self.phone_number} receive")
            print()
            print("For continuous operation, you can run the daemon:")
            print(f"  signal-cli -a {self.phone_number} daemon")
            print()
            print("Or set up a simple cron job (every 5 minutes):")
            print(f"*/5 * * * * signal-cli -a {self.phone_number} receive")
        else:
            print("\n=== Linked Device Setup Complete ===")
            print("Your device is now linked! For ongoing use, you can:")
            print("  signal-cli -a $ACCOUNT receive  # Run manually when needed")
            print("  signal-cli -a $ACCOUNT daemon   # Run continuously")
            print()
            print("Note: Replace $ACCOUNT with your actual phone number")
    
    def run_wizard(self):
        """Run the interactive wizard"""
        print("=== Signal CLI Setup ===")
        print("Choose setup mode:")
        print("1) Register new Signal account (becomes primary device)")
        print("2) Add Signal Desktop as linked device (addDevice)")
        print()
        
        while True:
            choice = input("Enter choice (1 or 2): ").strip()
            if choice == "1":
                print("Selected: New account registration")
                if not self.phone_number:
                    self.phone_number = input("Enter phone number (e.g., +1234567890): ").strip()
                print(f"Phone number: {self.phone_number}")
                self.register_new_account()
                break
            elif choice == "2":
                print("Selected: Add Signal Desktop as linked device")
                print("(You'll scan a QR code from Signal Desktop)")
                if not self.phone_number:
                    self.phone_number = input("Enter phone number (e.g., +1234567890): ").strip()
                print(f"Phone number: {self.phone_number}")
                self.add_device()
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    
    def register_new_account(self):
        """Register a new Signal account"""
        print(f"\n=== New Account Registration ===")
        print(f"Phone number: {self.phone_number}")
        print()
        
        if not self.check_signal_cli():
            return
        
        captcha_token = self.get_captcha_token()
        
        # Try SMS registration first
        if not self.register_sms(captcha_token):
            # If SMS fails, try voice
            self.register_voice(captcha_token)
        
        # Verify the code
        if not self.verify_code():
            return
        
        # Test the registration
        self.test_registration()
        
        # Provide daemon setup info
        self.setup_daemon_info(is_primary=True)
        
        print("\n=== Registration Complete ===")
        print("Your Signal CLI is now registered and ready to use!")
        print("Account data is stored in: ~/.local/share/signal-cli/data/")
    
    def add_device(self):
        """Add Signal Desktop as a linked device to this signal-cli primary device"""
        print(f"\n=== Link Signal Desktop to Signal CLI ===")
        print(f"Phone number: {self.phone_number}")
        print()
        print("This will make Signal Desktop a secondary device linked to your signal-cli.")
        print("Your signal-cli will remain the primary device.")
        print()
        
        if not self.check_signal_cli():
            return
        
        # Check if this account is registered
        try:
            result = subprocess.run(['signal-cli', 'listAccounts'], 
                                  capture_output=True, text=True, check=True)
            if self.phone_number not in result.stdout:
                print(f"Error: Account {self.phone_number} is not registered in signal-cli")
                print("Please register the account first using option 1")
                return
        except subprocess.CalledProcessError:
            print("Error: Could not check registered accounts")
            return
        
        print("✓ Account verified in signal-cli")
        print()
        
        # Create profile directory name (phone number without +)
        profile_dir = self.phone_number.replace('+', '')
        user_data_dir = f"/Users/{os.getenv('USER', os.getenv('USERNAME', 'unknown'))}/Library/Application Support/Signal-Profile-{profile_dir}"
        
        print("=== Launching Signal Desktop ===")
        print(f"Profile directory: {user_data_dir}")
        print()
        
        # Launch Signal Desktop with the specific profile
        try:
            print("Launching Signal Desktop...")
            # Launch in background but redirect output to avoid cluttering terminal
            subprocess.Popen([
                '/Applications/Signal.app/Contents/MacOS/Signal',
                f'--user-data-dir={user_data_dir}'
            ], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✓ Signal Desktop launched in background")
        except Exception as e:
            print(f"Error launching Signal Desktop: {e}")
            print("Please launch Signal Desktop manually and continue")
        
        print()
        print("=== Desktop Linking Instructions ===")
        print("To link Signal Desktop to your signal-cli:")
        print()
        print("1. Signal Desktop should now be open with the correct profile")
        print("2. Go to File > Preferences > Privacy > Linked devices > Link new device")
        print("3. A QR code will appear")
        print()
        
        # Try to automatically read QR code if qr_utils is available
        link_uri = None
        if QR_UTILS_AVAILABLE:
            print("4. QR code detected! Taking screenshot to read it automatically...")
            print("   (You'll see a screenshot selector - draw a square around the QR code)")
            
            # Try QR reading with option to retry
            qr_attempts = 0
            max_qr_attempts = 2
            
            while qr_attempts < max_qr_attempts and not link_uri:
                qr_attempts += 1
                if qr_attempts > 1:
                    print(f"\n🔄 QR code reading attempt {qr_attempts}/{max_qr_attempts}")
                
                try:
                    qr_data = qr_utils.copy_qr_code_from_screenshot()
                    if qr_data and qr_data.startswith('sgnl://linkdevice?'):
                        link_uri = qr_data
                        print(f"✅ QR code read successfully: {qr_data[:50]}...")
                    else:
                        print("⚠️  QR code read but doesn't appear to be a valid linking URI")
                        print("   QR data received: ", qr_data)
                        
                        if qr_attempts < max_qr_attempts:
                            retry = input("   Would you like to try again? (y/n): ").strip().lower()
                            if retry not in ['y', 'yes']:
                                print("   Skipping to manual input...")
                                break
                        else:
                            print("   Maximum attempts reached, falling back to manual input...")
                            
                except Exception as e:
                    if qr_attempts < max_qr_attempts:
                        retry = input("   Would you like to try again? (y/n): ").strip().lower()
                        if retry not in ['y', 'yes']:
                            print("   Skipping to manual input...")
                            break
                    else:
                        print("   Maximum attempts reached, falling back to manual input...")
        
        # Fall back to manual input if automatic reading failed or isn't available
        if not link_uri:
            print()
            print("=== Manual URI Input Required ===")
            print("4. Copy the linking URI that appears in Signal Desktop")
            print("   (It should start with 'sgnl://linkdevice?')")
            print()
            print("5. Enter the linking URI below:")
            print()
            
            # Get the linking URI from user
            while True:
                link_uri = input("Enter the linking URI from Signal Desktop: ").strip()
                if not link_uri:
                    print("Error: URI cannot be empty. Please enter the linking URI.")
                    continue
                elif link_uri.startswith('sgnl://linkdevice?'):
                    print("✅ Valid linking URI detected")
                    break
                else:
                    print("Error: URI should start with 'sgnl://linkdevice?'")
                    print("Please check the URI and try again")
                    print("Example format: sgnl://linkdevice?uuid=...&pub_key=...")
        
        print()
        print("=== Linking Device ===")
        print("Adding Signal Desktop as a linked device...")
        
        try:
            # Use addDevice command to link the device
            result = subprocess.run([
                'signal-cli', '-a', self.phone_number, 'addDevice', '--uri', link_uri
            ], capture_output=True, text=True, check=True)
            
            print("✓ Device linking successful!")
            print()
            print("=== Syncing Data ===")
            print("Downloading contacts and groups from Signal Desktop...")
            
            # Run receive to sync data
            print("Syncing data...")
            try:
                subprocess.run([
                    'signal-cli', '-a', self.phone_number, 'receive'
                ], timeout=10, check=True)
                print("✓ Sync completed")
            except subprocess.TimeoutExpired:
                print("Sync timeout (this is normal)")
            except subprocess.CalledProcessError:
                print("Sync error (this is normal for initial setup)")
            
            print()
            print("=== Setup Complete ===")
            print("Signal Desktop is now linked to your signal-cli!")
            print("Your signal-cli remains the primary device with full control.")
            print("Signal Desktop is now a secondary device for convenient messaging.")
            print()
            print("You can manage linked devices with:")
            print("  signal-cli -a", self.phone_number, "listDevices")
            print("  signal-cli -a", self.phone_number, "removeDevice -d DEVICE_ID")
            
        except subprocess.CalledProcessError as e:
            print(f"Error linking device: {e}")
            print("Make sure:")
            print("1. The URI is correct and starts with 'sgnl://linkdevice?'")
            print("2. You're running this from the signal-cli account you want to link from")
            print("3. The QR code hasn't expired (generate a new one if needed)")
            return
    
    def run_with_params(self, mode: str, phone_number: str, captcha_token: Optional[str] = None):
        """Run with command line parameters"""
        self.phone_number = phone_number
        
        if mode == "register":
            if not captcha_token:
                print("Error: Captcha token is required for registration")
                sys.exit(1)
            
            if not self.check_signal_cli():
                sys.exit(1)
            
            # Try SMS registration first
            if not self.register_sms(captcha_token):
                # If SMS fails, try voice
                if not self.register_voice(captcha_token):
                    sys.exit(1)
            
            print("\n=== Registration Initiated ===")
            print("Please check your phone for the verification code.")
            print("Waiting for verification code...")
            
            # Wait for verification code and complete registration
            if self.verify_code():
                # Test the registration
                self.test_registration()
                self.setup_daemon_info(is_primary=True)
                print("\n=== Registration Complete ===")
                print("Your Signal CLI is now registered and ready to use!")
                print("Account data is stored in: ~/.local/share/signal-cli/data/")
            else:
                print("\n=== Registration Failed ===")
                print("Verification failed. Please try again.")
                sys.exit(1)
            
        elif mode == "verify":
            print("Note: Verification is now part of the registration process.")
            print("Use 'register' mode instead to complete the full registration.")
            sys.exit(1)
                
        elif mode == "addDevice":
            if not self.check_signal_cli():
                sys.exit(1)
            
            self.add_device()


def main():
    parser = argparse.ArgumentParser(
        description="Signal CLI Registration Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive wizard mode
  python3 register-number.py

  # Register new account with parameters
  python3 register-number.py register +1234567890 --captcha <token>

  # Register using captcha token from file (recommended for long tokens)
  python3 register-number.py register +1234567890 --captcha-file captcha.txt

  # Add Signal Desktop as linked device (addDevice)
  # Automatically reads QR code from screenshot, or manual URI input
  python3 register-number.py addDevice +1234567890

Note: For captcha tokens, you can:
1. Paste the full line from the browser console
2. Paste just the token part
3. Save the token to a file and use --captcha-file (recommended for very long tokens)
        """
    )
    
    parser.add_argument('mode', nargs='?', choices=['register', 'addDevice'],
                       help='Operation mode (register or addDevice)')
    parser.add_argument('phone_number', nargs='?', 
                       help='Phone number in international format (e.g., +1234567890)')
    parser.add_argument('--captcha', help='Captcha token for registration')
    parser.add_argument('--captcha-file', help='File containing captcha token (alternative to --captcha)')
    parser.add_argument('--pin', help='Registration PIN')
    parser.add_argument('--device-name', default='signal-cli-desktop',
                       help='Device name for linking (default: signal-cli-desktop)')

    
    args = parser.parse_args()
    
    # If no arguments provided, run wizard mode
    if not args.mode:
        registration = SignalCLIRegistration()
        registration.run_wizard()
        return
    
    # Parameter mode
    if not args.phone_number:
        print("Error: Phone number is required for parameter mode")
        parser.print_help()
        sys.exit(1)
    
    registration = SignalCLIRegistration()
    registration.device_name = args.device_name
    
    if args.mode == "register":
        # Handle captcha token from file or direct input
        captcha_token = args.captcha
        if args.captcha_file:
            try:
                captcha_token = registration.read_captcha_from_file(args.captcha_file)
                print(f"✓ Captcha token loaded from file: {args.captcha_file}")
            except ValueError as e:
                print(f"Error reading captcha file: {e}")
                sys.exit(1)
        
        registration.run_with_params("register", args.phone_number, captcha_token)
    elif args.mode == "addDevice":
        registration.phone_number = args.phone_number
        registration.add_device()


if __name__ == "__main__":
    main()
