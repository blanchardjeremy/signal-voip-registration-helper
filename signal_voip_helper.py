#!/usr/bin/env python3
"""
Signal CLI Interface
Handles all user interactions for Signal CLI registration and device linking
"""

import argparse
import sys
import os
from typing import Optional, Tuple

# Import the core modules
from signal_registration import (
    SignalCLICore, 
    RegistrationConfig, 
    AppConfig,
    SignalCLINotFoundError,
    RegistrationFailedError,
    VerificationFailedError,
    DeviceLinkingError,
    SignalRegistrationError,
    get_captcha_instructions,
    get_daemon_setup_info,
    get_linking_instructions
)

try:
    import qr_utils
    QR_UTILS_AVAILABLE = True
except ImportError:
    QR_UTILS_AVAILABLE = False

try:
    from create_signal_launcher import SignalAppBuilder
    APP_BUILDER_AVAILABLE = True
except ImportError:
    APP_BUILDER_AVAILABLE = False


class SignalCLIInterface:
    """Handles all user interactions for Signal CLI operations"""
    
    def __init__(self):
        self.core = None
        self.config = None
    
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n=== {title} ===")
    
    def print_error(self, message: str):
        """Print an error message"""
        print(f"❌ {message}")
    
    def print_success(self, message: str):
        """Print a success message"""
        print(f"✅ {message}")
    
    def print_warning(self, message: str):
        """Print a warning message"""
        print(f"⚠️  {message}")
    
    def print_info(self, message: str):
        """Print an info message"""
        print(f"ℹ️  {message}")
    
    def get_phone_number(self) -> str:
        """Get phone number from user"""
        while True:
            phone_number = input("Enter phone number (e.g., +1234567890): ").strip()
            if phone_number and phone_number.startswith('+') and len(phone_number) > 5:
                return phone_number
            print("Please enter a valid phone number starting with + (e.g., +1234567890)")
    
    def get_captcha_token(self) -> str:
        """Get captcha token from user with instructions"""
        self.print_header("Captcha Token Required")
        print(get_captcha_instructions())
        print()
        print("Note: If pasting the long token causes issues, try pasting it in smaller parts")
        print("or save it to a file and use --captcha-file option")
        print()
        
        while True:
            try:
                captcha_input = input("Enter captcha token or full line: ").strip()
                if not captcha_input:
                    self.print_error("Captcha token cannot be empty")
                    continue
                
                # Extract token from the full line if provided
                captcha_token = self.core.extract_captcha_token(captcha_input)
                if captcha_token:
                    self.print_success("Captcha token extracted successfully")
                    return captcha_token
                else:
                    self.print_error("Could not extract captcha token from input")
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
    
    def get_verification_code(self) -> str:
        """Get verification code from user"""
        while True:
            verification_code = input("Enter the 6-digit verification code you received: ").strip()
            if verification_code and len(verification_code) == 6 and verification_code.isdigit():
                return verification_code
            self.print_error("Please enter a valid 6-digit verification code")
    
    def get_pin_code(self) -> Optional[str]:
        """Get PIN code from user if they have one"""
        has_pin = input("Do you have a registration PIN? (y/n): ").strip().lower()
        if has_pin in ['y', 'yes']:
            return input("Enter your PIN: ").strip()
        return None
    
    def get_app_config_for_adddevice(self, phone_number: str) -> Tuple[AppConfig, bool]:
        """Get app configuration for addDevice flow - all prompts at beginning"""
        create_app = False
        app_config = None
        copy_to_applications = False
        
        if not APP_BUILDER_AVAILABLE:
            self.print_warning("Launcher creation not available - create_signal_launcher.py not found")
            return None, False
        
        self.print_header("Signal Desktop App Configuration")
        print("Would you like to create a Signal Desktop .app file for easy launching?")
        print("This will create a clickable app that launches Signal with your profile.")
        print()
        
        create_choice = input("Create Signal Desktop app? (y/n): ").strip().lower()
        if create_choice not in ['y', 'yes']:
            return None, False
        
        create_app = True
        phone_number_without_plus = phone_number.replace('+', '')
        
        print()
        print("Choose a name for your Signal app:")
        print(f"Default: Signal-{phone_number_without_plus}.app")
        print("Custom name examples: work, personal, family, etc.")
        print()
        
        app_name = input(f"Nickname for this Signal app [Default: {phone_number_without_plus}]: ").strip()
        if not app_name:
            app_name = None
        
        # Ask about copying to Applications folder upfront
        print()
        copy_choice = input("Copy the app to your Applications folder after creation? (y/n): ").strip().lower()
        copy_to_applications = copy_choice in ['y', 'yes']
        
        app_config = AppConfig(
            phone_number=phone_number,
            app_name=app_name,
            output_dir=None
        )
        
        return app_config, copy_to_applications
    
    def get_linking_uri_manually(self) -> str:
        """Get linking URI from user manual input"""
        print("\n=== Manual URI Input Required ===")
        print("4. Copy the linking URI that appears in Signal Desktop")
        print("   (It should start with 'sgnl://linkdevice?')")
        print()
        print("5. Enter the linking URI below:")
        print()
        
        while True:
            link_uri = input("Enter the linking URI from Signal Desktop: ").strip()
            if not link_uri:
                self.print_error("URI cannot be empty. Please enter the linking URI.")
                continue
            elif link_uri.startswith('sgnl://linkdevice?'):
                self.print_success("Valid linking URI detected")
                return link_uri
            else:
                self.print_error("URI should start with 'sgnl://linkdevice?'")
                print("Please check the URI and try again")
                print("Example format: sgnl://linkdevice?uuid=...&pub_key=...")
    
    def get_linking_uri(self) -> str:
        """Get linking URI either automatically or manually"""
        if QR_UTILS_AVAILABLE and self.core.check_qr_utilities():
            print("4. QR code detected! Taking screenshot to read it automatically...")
            print("   (You'll see a screenshot selector - draw a square around the QR code)")
            
            qr_attempts = 0
            max_qr_attempts = 2
            
            while qr_attempts < max_qr_attempts:
                qr_attempts += 1
                if qr_attempts > 1:
                    print(f"\n🔄 QR code reading attempt {qr_attempts}/{max_qr_attempts}")
                
                try:
                    qr_data = self.core.read_qr_code_automatically()
                    if qr_data and qr_data.startswith('sgnl://linkdevice?'):
                        print(f"✅ QR code read successfully: {qr_data[:50]}...")
                        return qr_data
                    else:
                        print("⚠️  QR code read but doesn't appear to be a valid linking URI")
                        if qr_data:
                            print("   QR data received:", qr_data)
                        
                        if qr_attempts < max_qr_attempts:
                            retry = input("   Would you like to try again? (y/n): ").strip().lower()
                            if retry not in ['y', 'yes']:
                                print("   Skipping to manual input...")
                                break
                        else:
                            print("   Maximum attempts reached, falling back to manual input...")
                            
                except Exception as e:
                    print(f"⚠️  Error reading QR code: {e}")
                    if qr_attempts < max_qr_attempts:
                        retry = input("   Would you like to try again? (y/n): ").strip().lower()
                        if retry not in ['y', 'yes']:
                            print("   Skipping to manual input...")
                            break
                    else:
                        print("   Maximum attempts reached, falling back to manual input...")
        
        # Fall back to manual input
        return self.get_linking_uri_manually()
    
    def run_wizard(self):
        """Run the interactive wizard"""
        self.print_header("Signal CLI Setup")
        print("Choose setup mode:")
        print("1) Register new Signal account (becomes primary device)")
        print("2) Add Signal Desktop as linked device (addDevice)")
        print()
        
        while True:
            choice = input("Enter choice (1 or 2): ").strip()
            if choice == "1":
                print("Selected: New account registration")
                phone_number = self.get_phone_number()
                print(f"Phone number: {phone_number}")
                self.register_new_account_interactive(phone_number)
                break
            elif choice == "2":
                print("Selected: Add Signal Desktop as linked device")
                print("(You'll scan a QR code from Signal Desktop)")
                phone_number = self.get_phone_number()
                print(f"Phone number: {phone_number}")
                self.add_device_interactive(phone_number)
                break
            else:
                self.print_error("Invalid choice. Please enter 1 or 2.")
    
    def register_new_account_interactive(self, phone_number: str):
        """Interactive new account registration"""
        self.print_header("New Account Registration")
        print(f"Phone number: {phone_number}")
        print()
        
        # Setup core
        self.config = RegistrationConfig(phone_number=phone_number)
        self.core = SignalCLICore(self.config)
        
        try:
            # Check prerequisites
            self.core.check_signal_cli()
            self.print_success("signal-cli found")
            
            # Get captcha token
            captcha_token = self.get_captcha_token()
            
            # Get verification info upfront
            print("\nNow we'll start the registration process.")
            print("You'll receive a verification code via SMS or voice call.")
            input("Press Enter when ready to proceed...")
            
            # Try registration
            self.print_header("Registering with SMS")
            if not self.core.register_sms(captcha_token):
                self.print_warning("SMS registration failed, trying voice verification")
                self.print_header("Registering with Voice Call")
                print("Waiting 60 seconds before attempting voice verification...")
                if not self.core.register_voice(captcha_token):
                    raise RegistrationFailedError("Both SMS and voice registration failed")
                else:
                    self.print_success("Voice call registration initiated")
                    print("You should receive a call shortly with the verification code")
            else:
                self.print_success("Registration request sent via SMS")
            
            # Get verification code and PIN
            self.print_header("Verification")
            verification_code = self.get_verification_code()
            pin_code = self.get_pin_code()
            
            # Verify
            if self.core.verify_registration(verification_code, pin_code):
                if pin_code:
                    self.print_success("Account verified successfully with PIN")
                else:
                    self.print_success("Account verified successfully")
            
            # Test registration
            self.print_header("Testing Registration")
            if self.core.test_registration():
                self.print_success("Test message sent successfully")
                print("Check your Signal app for the test message")
            else:
                self.print_warning("Could not send test message, but registration may still be successful")
            
            # Show daemon info
            self.print_header("Important: Regular Message Receiving")
            print(get_daemon_setup_info(phone_number, is_primary=True))
            
            self.print_header("Registration Complete")
            self.print_success("Your Signal CLI is now registered and ready to use!")
            print("Account data is stored in: ~/.local/share/signal-cli/data/")
            
        except SignalCLINotFoundError as e:
            self.print_error(str(e))
        except (RegistrationFailedError, VerificationFailedError) as e:
            self.print_error(str(e))
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
    
    def add_device_interactive(self, phone_number: str):
        """Interactive device linking with consolidated prompts at the beginning"""
        self.print_header("Link Signal Desktop to Signal CLI")
        print(f"Phone number: {phone_number}")
        print()
        print("This will make Signal Desktop a secondary device linked to your signal-cli.")
        print("Your signal-cli will remain the primary device.")
        print()
        
        # Setup core
        self.config = RegistrationConfig(phone_number=phone_number)
        self.core = SignalCLICore(self.config)
        
        try:
            # Check prerequisites
            self.core.check_signal_cli()
            self.print_success("signal-cli found")
            
            if not self.core.verify_account_registered():
                raise SignalRegistrationError(
                    f"Account {phone_number} is not registered in signal-cli. "
                    "Please register the account first using option 1"
                )
            self.print_success("Account verified in signal-cli")
            
            # Get all configuration upfront
            app_config, copy_to_applications = self.get_app_config_for_adddevice(phone_number)
            
            print()
            self.print_info("All configuration collected. Starting device linking process...")
            
            # Create Signal Desktop app if requested
            created_app_name = None
            if app_config:
                self.print_header("Creating Signal Desktop App")
                app_path, created_app_name = self.core.create_signal_app(app_config)
                self.print_success(f"Created Signal app: {created_app_name}")
                print(f"📁 Location: {app_path}")
                print()
                print("You can now:")
                print("1. Double-click the app to launch Signal with your profile")
                print("2. Drag it to your Applications folder")
                print("3. Add it to your Dock for quick access")
            
            # Launch Signal Desktop
            self.print_header("Launching Signal Desktop")
            user_data_dir = self.core.launch_signal_desktop()
            print(f"Profile directory: {user_data_dir}")
            print()
            self.print_success("Signal Desktop launched in background")
            
            # Show linking instructions
            print(get_linking_instructions())
            
            # Get linking URI
            link_uri = self.get_linking_uri()
            
            # Link the device
            self.print_header("Linking Device")
            print("Adding Signal Desktop as a linked device...")
            if self.core.link_device_to_signal_cli(link_uri):
                self.print_success("Device linking successful!")
            
            # Sync data
            self.print_header("Syncing Data")
            print("Downloading contacts and groups from Signal Desktop...")
            self.core.sync_signal_data()
            self.print_success("Sync completed")
            
            # Show completion message
            self.print_header("Setup Complete")
            self.print_success("Signal Desktop is now linked to your signal-cli!")
            print("Your signal-cli remains the primary device with full control.")
            print("Signal Desktop is now a secondary device for convenient messaging.")
            print()
            
            # Handle app copying if requested
            if created_app_name and copy_to_applications:
                print("Copying app to Applications folder...")
                if self.core.copy_app_to_applications(created_app_name):
                    self.print_success(f"Successfully copied {created_app_name} to /Applications")
                    print("📱 You can now launch Signal from Applications or add to Dock")
                else:
                    self.print_error(f"Could not copy {created_app_name} to Applications")
                    print(f"📱 Manual step: Drag {created_app_name} to /Applications when you find it")
                print()
            elif created_app_name:
                print("📱 Manual step:")
                print(f"   Drag {created_app_name} from the current directory to /Applications")
                print()
            
            if created_app_name:
                print(f"You can launch {created_app_name} from your Applications folder or Dock")
            
            print("🎉 Success! You're done!")
            
        except (SignalCLINotFoundError, DeviceLinkingError, SignalRegistrationError) as e:
            self.print_error(str(e))
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
    
    def run_with_params(self, mode: str, phone_number: str, captcha_token: Optional[str] = None, 
                       captcha_file: Optional[str] = None, device_name: str = "signal-cli-desktop"):
        """Run with command line parameters"""
        self.config = RegistrationConfig(phone_number=phone_number, device_name=device_name)
        self.core = SignalCLICore(self.config)
        
        try:
            if mode == "register":
                if not captcha_token and not captcha_file:
                    self.print_error("Captcha token is required for registration")
                    sys.exit(1)
                
                # Handle captcha token from file if provided
                if captcha_file:
                    try:
                        captcha_token = self.core.read_captcha_from_file(captcha_file)
                        self.print_success(f"Captcha token loaded from file: {captcha_file}")
                    except ValueError as e:
                        self.print_error(f"Error reading captcha file: {e}")
                        sys.exit(1)
                
                self.core.check_signal_cli()
                
                # Try registration
                if not self.core.register_sms(captcha_token):
                    if not self.core.register_voice(captcha_token):
                        self.print_error("Both SMS and voice registration failed")
                        sys.exit(1)
                
                self.print_header("Registration Initiated")
                print("Please check your phone for the verification code.")
                print("Waiting for verification code...")
                
                # Wait for verification code and complete registration
                verification_code = self.get_verification_code()
                pin_code = self.get_pin_code()
                
                if self.core.verify_registration(verification_code, pin_code):
                    # Test the registration
                    self.core.test_registration()
                    print(get_daemon_setup_info(phone_number, is_primary=True))
                    self.print_header("Registration Complete")
                    self.print_success("Your Signal CLI is now registered and ready to use!")
                    print("Account data is stored in: ~/.local/share/signal-cli/data/")
                else:
                    self.print_header("Registration Failed")
                    self.print_error("Verification failed. Please try again.")
                    sys.exit(1)
                
            elif mode == "addDevice":
                self.add_device_interactive(phone_number)
            
        except (SignalCLINotFoundError, RegistrationFailedError, VerificationFailedError, 
                DeviceLinkingError, SignalRegistrationError) as e:
            self.print_error(str(e))
            sys.exit(1)
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Signal CLI Registration Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive wizard mode
  python3 signal_voip_helper.py

  # Register new account with parameters
  python3 signal_voip_helper.py register +1234567890 --captcha <token>

  # Register using captcha token from file (recommended for long tokens)
  python3 signal_voip_helper.py register +1234567890 --captcha-file captcha.txt

  # Add Signal Desktop as linked device (addDevice)
  # Automatically reads QR code from screenshot, or manual URI input
  python3 signal_voip_helper.py addDevice +1234567890

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
    parser.add_argument('--pin', help='Registration PIN (deprecated - will be prompted interactively)')
    parser.add_argument('--device-name', default='signal-cli-desktop',
                       help='Device name for linking (default: signal-cli-desktop)')
    
    args = parser.parse_args()
    
    interface = SignalCLIInterface()
    
    # If no arguments provided, run wizard mode
    if not args.mode:
        interface.run_wizard()
        return
    
    # Parameter mode
    if not args.phone_number:
        print("❌ Error: Phone number is required for parameter mode")
        parser.print_help()
        sys.exit(1)
    
    interface.run_with_params(
        args.mode, 
        args.phone_number, 
        args.captcha,
        args.captcha_file,
        args.device_name
    )


if __name__ == "__main__":
    main()
