#!/usr/bin/env python3
"""
Signal CLI Registration Core Module
Provides core functionality for Signal CLI registration and device linking
"""

import subprocess
import time
import os
from typing import Optional, Tuple
from dataclasses import dataclass

# Import optional dependencies
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


@dataclass
class RegistrationConfig:
    """Configuration for registration process"""
    phone_number: str
    device_name: str = "signal-cli-desktop"
    captcha_url: str = "https://signalcaptchas.org/registration/generate.html"


@dataclass
class AppConfig:
    """Configuration for Signal app creation"""
    phone_number: str
    app_name: Optional[str] = None
    output_dir: Optional[str] = None


class SignalRegistrationError(Exception):
    """Base exception for Signal registration errors"""
    pass


class SignalCLINotFoundError(SignalRegistrationError):
    """Raised when signal-cli is not found"""
    pass


class RegistrationFailedError(SignalRegistrationError):
    """Raised when registration fails"""
    pass


class VerificationFailedError(SignalRegistrationError):
    """Raised when verification fails"""
    pass


class DeviceLinkingError(SignalRegistrationError):
    """Raised when device linking fails"""
    pass


class SignalCLICore:
    """Core Signal CLI registration functionality without user interactions"""
    
    def __init__(self, config: RegistrationConfig):
        self.config = config
        self.created_app_name = None
        self.created_app_path = None
    
    def check_signal_cli(self) -> bool:
        """Check if signal-cli is installed and accessible"""
        try:
            subprocess.run(['signal-cli', '--version'], 
                          capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise SignalCLINotFoundError(
                "signal-cli is not installed or not in PATH. "
                "Please install signal-cli first: "
                "wget https://github.com/AsamK/signal-cli/releases/latest"
            )
    
    def check_qr_utilities(self) -> bool:
        """Check if QR utilities are available and working"""
        if not QR_UTILS_AVAILABLE:
            return False
        
        try:
            if hasattr(qr_utils, 'check_dependencies'):
                return qr_utils.check_dependencies()
            else:
                return True
        except Exception:
            return False
    
    def check_brew_dependencies(self) -> bool:
        """Check if required brew dependencies are installed"""
        required_packages = {
            'signal-cli': 'signal-cli',
            'zbarimg': 'zbar'
        }
        
        missing_packages = []
        
        for command, package in required_packages.items():
            try:
                result = subprocess.run(['which', command], 
                                      capture_output=True, text=True, check=False)
                if result.returncode != 0:
                    missing_packages.append(package)
            except Exception:
                missing_packages.append(package)
        
        if missing_packages:
            print("❌ Missing required dependencies:")
            print()
            for package in missing_packages:
                print(f"   • {package}")
            print()
            print("💡 Install missing dependencies with:")
            print(f"   brew install {' '.join(missing_packages)}")
            print()
            return False
        
        return True
    
    def check_signal_desktop_running(self) -> bool:
        """Check if Signal Desktop is currently running on macOS"""
        try:
            # Use pgrep to check for Signal processes
            result = subprocess.run(['pgrep', '-f', 'Signal.app'], 
                                  capture_output=True, text=True, check=False)
            return result.returncode == 0
        except Exception:
            # Fallback to ps aux if pgrep fails
            try:
                result = subprocess.run(['ps', 'aux'], 
                                      capture_output=True, text=True, check=False)
                return 'Signal.app' in result.stdout
            except Exception:
                # If both methods fail, assume Signal is not running
                return False
    
    def quit_signal_desktop(self) -> bool:
        """Attempt to quit Signal Desktop gracefully"""
        try:
            # First try using AppleScript to quit gracefully
            subprocess.run([
                'osascript', '-e', 'tell application "Signal" to quit'
            ], capture_output=True, text=True, check=True)
            
            # Wait a moment for graceful quit
            time.sleep(2)
            
            # Check if it actually quit
            if not self.check_signal_desktop_running():
                return True
            
            # If graceful quit didn't work, try force quit
            result = subprocess.run(['pgrep', '-f', 'Signal.app'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        subprocess.run(['kill', pid.strip()], check=False)
                
                # Wait and check again
                time.sleep(1)
                return not self.check_signal_desktop_running()
            
            return True
            
        except Exception:
            # If all else fails, return False
            return False
    
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
        try:
            subprocess.run([
                'signal-cli', '-a', self.config.phone_number, 'register',
                '--captcha', f"signalcaptcha://{captcha_token}"
            ], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def register_voice(self, captcha_token: str) -> bool:
        """Register with voice call verification"""
        # Wait 60 seconds before attempting voice verification
        time.sleep(60)
        
        try:
            subprocess.run([
                'signal-cli', '-a', self.config.phone_number, 'register',
                '--voice', '--captcha', f"signalcaptcha://{captcha_token}"
            ], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def verify_registration(self, verification_code: str, pin_code: Optional[str] = None) -> bool:
        """Verify the registration with code and optional PIN"""
        try:
            if pin_code:
                subprocess.run([
                    'signal-cli', '-a', self.config.phone_number, 'verify',
                    verification_code, '--pin', pin_code
                ], check=True)
            else:
                subprocess.run([
                    'signal-cli', '-a', self.config.phone_number, 'verify', verification_code
                ], check=True)
            return True
        except subprocess.CalledProcessError:
            raise VerificationFailedError("Registration verification failed")
    
    def test_registration(self) -> bool:
        """Test the registration by sending a test message"""
        try:
            subprocess.run([
                'signal-cli', '-a', self.config.phone_number, 'send',
                '--note-to-self', '-m', 'Test message - Signal CLI registration successful!'
            ], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def verify_account_registered(self) -> bool:
        """Verify that the account has at least one device registered in signal-cli"""
        try:
            result = subprocess.run(['signal-cli', '-a', self.config.phone_number, 'listDevices'], 
                                  capture_output=True, text=True, check=True)
            # Check if we have at least one device (look for "Device" in output)
            return "Device" in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    def launch_signal_desktop(self) -> str:
        """Launch Signal Desktop with specific profile and return profile directory"""
        profile_dir = self.config.phone_number.replace('+', '')
        user_data_dir = f"/Users/{os.getenv('USER', os.getenv('USERNAME', 'unknown'))}/Library/Application Support/Signal-Profile-{profile_dir}"
        
        try:
            subprocess.Popen([
                '/Applications/Signal.app/Contents/MacOS/Signal',
                f'--user-data-dir={user_data_dir}'
            ], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            raise SignalRegistrationError(f"Failed to launch Signal Desktop: {e}")
        
        return user_data_dir
    
    def read_qr_code_automatically(self) -> Optional[str]:
        """Try to read QR code automatically if qr_utils is available"""
        if not QR_UTILS_AVAILABLE:
            return None
        
        qr_attempts = 0
        max_qr_attempts = 2
        
        while qr_attempts < max_qr_attempts:
            qr_attempts += 1
            
            try:
                qr_data = qr_utils.copy_qr_code_from_screenshot()
                if qr_data and qr_data.startswith('sgnl://linkdevice?'):
                    return qr_data
                else:
                    if qr_attempts < max_qr_attempts:
                        # In the refactored version, we'll let the UI handle retry logic
                        continue
                    else:
                        break
                        
            except Exception:
                if qr_attempts < max_qr_attempts:
                    continue
                else:
                    break
        
        return None
    
    def link_device_to_signal_cli(self, link_uri: str) -> bool:
        """Link the device using signal-cli"""
        try:
            subprocess.run([
                'signal-cli', '-a', self.config.phone_number, 'addDevice', '--uri', link_uri
            ], capture_output=True, text=True, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            raise DeviceLinkingError(f"Device linking failed: {e}")
    
    def sync_signal_data(self) -> bool:
        """Sync contacts and groups from Signal Desktop"""
        try:
            subprocess.run([
                'signal-cli', '-a', self.config.phone_number, 'receive'
            ], timeout=10, check=True)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            # This is normal for initial setup
            return True
    
    def create_signal_app(self, app_config: AppConfig) -> Tuple[str, str]:
        """Create Signal Desktop .app file and return (app_path, app_name)"""
        if not APP_BUILDER_AVAILABLE:
            raise SignalRegistrationError("SignalAppBuilder not available")
        
        builder = SignalAppBuilder()
        app_path = builder.create_app_bundle(
            app_config.phone_number, 
            output_dir=app_config.output_dir,
            app_name=app_config.app_name
        )
        
        phone_number_without_plus = app_config.phone_number.replace('+', '')
        if app_config.app_name:
            app_name = f"Signal-{app_config.app_name}.app"
        else:
            app_name = f"Signal-{phone_number_without_plus}.app"
        
        self.created_app_path = app_path
        self.created_app_name = app_name
        
        return app_path, app_name
    
    def copy_app_to_applications(self, app_name: str) -> bool:
        """Copy the created app to Applications folder"""
        try:
            import shutil
            source_path = f"./{app_name}"
            dest_path = f"/Applications/{app_name}"
            
            if os.path.exists(source_path):
                shutil.copytree(source_path, dest_path)
                return True
            else:
                return False
                
        except Exception:
            return False
    
    def register_new_account(self, captcha_token: str, verification_code: str, pin_code: Optional[str] = None) -> bool:
        """Complete new account registration process"""
        self.check_signal_cli()
        
        # Try SMS registration first
        if not self.register_sms(captcha_token):
            # If SMS fails, try voice
            if not self.register_voice(captcha_token):
                raise RegistrationFailedError("Both SMS and voice registration failed")
        
        # Verify the code
        if not self.verify_registration(verification_code, pin_code):
            raise VerificationFailedError("Registration verification failed")
        
        # Test the registration
        test_success = self.test_registration()
        
        return test_success
    
    def add_device(self, link_uri: str, app_config: Optional[AppConfig] = None) -> Tuple[str, Optional[str]]:
        """Add Signal Desktop as a linked device"""
        self.check_signal_cli()
        
        if not self.verify_account_registered():
            raise SignalRegistrationError(
                f"Account {self.config.phone_number} is not registered in signal-cli. "
                "Please register the account first."
            )
        
        created_app_path = None
        created_app_name = None
        
        # Create Signal Desktop app if config provided
        if app_config and APP_BUILDER_AVAILABLE:
            created_app_path, created_app_name = self.create_signal_app(app_config)
        
        # Launch Signal Desktop
        user_data_dir = self.launch_signal_desktop()
        
        # Link the device
        if not self.link_device_to_signal_cli(link_uri):
            raise DeviceLinkingError("Failed to link device")
        
        # Sync data
        self.sync_signal_data()
        
        return user_data_dir, created_app_name


# Helper functions for common use cases
def get_captcha_instructions() -> str:
    """Get captcha token instructions"""
    return """=== Captcha Token Required ===
1. Open this URL in your browser: https://signalcaptchas.org/registration/generate.html
2. Solve the captcha
3. Right click on the "Open Signal" link and click "Copy link address"
4. Copy the entire line or just the token part
"""


def get_daemon_setup_info(phone_number: str, is_primary: bool = True) -> str:
    """Get daemon setup information"""
    if is_primary:
        return f"""=== Important: Regular Message Receiving ===
Signal protocol requires regular message receiving for proper encryption.
You should regularly run:
  signal-cli -a {phone_number} receive

For continuous operation, you can run the daemon:
  signal-cli -a {phone_number} daemon

Or set up a simple cron job (every 5 minutes):
*/5 * * * * signal-cli -a {phone_number} receive"""
    else:
        return """=== Linked Device Setup Complete ===
Your device is now linked! For ongoing use, you can:
  signal-cli -a $ACCOUNT receive  # Run manually when needed
  signal-cli -a $ACCOUNT daemon   # Run continuously

Note: Replace $ACCOUNT with your actual phone number"""
