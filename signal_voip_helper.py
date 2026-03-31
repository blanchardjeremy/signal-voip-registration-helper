#!/usr/bin/env python3
"""
Signal CLI Interface
Modern CLI for Signal CLI registration and device linking
"""

import argparse
import sys
import os
import time
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field

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
)
from launcher_icon_catalog import (
    LAUNCHER_ICON_CHOICES,
    default_launcher_icon_id,
    launcher_icon_label,
)
from signal_receive_job import (
    install_receive_job,
    is_receive_job_installed,
    needs_receive_job_repair,
    uninstall_receive_job,
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


@dataclass
class UserConfig:
    """Configuration collected from user input"""
    phone_number: str
    operation_mode: str  # 'register' or 'addDevice'
    captcha_token: Optional[str] = None
    verification_code: Optional[str] = None
    pin_code: Optional[str] = None
    create_app: bool = False
    app_name: Optional[str] = None
    launcher_icon_id: str = field(default_factory=default_launcher_icon_id)
    copy_to_applications: bool = False
    device_name: str = "signal-cli-desktop"
    needs_verification: bool = True  # Will be set dynamically during registration


class ModernCLI:
    """Modern CLI interface utilities"""
    
    @staticmethod
    def print_box(title: str, message: str = "", width: int = 60):
        """Print a formatted box with title and optional message"""
        # Calculate title section length
        title_section = f"─ {title} "
        remaining_width = width - len(title_section) - 2  # -2 for the corner chars
        
        # Build the box
        top = f"┌{title_section}" + "─" * remaining_width + "┐"
        print(f"\n{top}")
        print(f"│{' ' * (width - 2)}│")
        
        if message:
            # Center the message in the box
            message_padding = (width - 2 - len(message)) // 2
            padded_message = " " * message_padding + message + " " * (width - 3 - len(message) - message_padding)
            print(f"│{padded_message}│")
            print(f"│{' ' * (width - 2)}│")
        
        bottom = "└" + "─" * (width - 2) + "┘"
        print(bottom)
    
    @staticmethod
    def box(title: str, width: int = 60) -> str:
        """Create a box with title - single line (deprecated, use print_box)"""
        top = f"┌─ {title} " + "─" * (width - len(title) - 4) + "┐"
        middle = f"│{' ' * (width - 2)}│"
        bottom = "└" + "─" * (width - 2) + "┘"
        return f"{top}\n{middle}\n{bottom}"
    
    @staticmethod
    def section_header(title: str, emoji: str = "✨") -> str:
        """Create a section header"""
        return f"\n{emoji} {title}\n"
    
    @staticmethod
    def progress_step(step: str, status: str = "in_progress") -> str:
        """Create a progress step indicator"""
        icons = {
            "pending": "○",
            "in_progress": "●", 
            "completed": "✓",
            "failed": "✗"
        }
        return f"{icons.get(status, '○')} {step}"
    
    @staticmethod
    def choice_option(key: str, title: str, description: str) -> str:
        """Format a choice option"""
        return f"  {key}  {title:<20} - {description}"
    
    @staticmethod
    def input_prompt(prompt: str, help_text: str = "") -> str:
        """Format an input prompt"""
        result = f"? {prompt}"
        if help_text:
            result += f"\n  ◦ {help_text}"
        return result + " › "


class SignalCLIInterface:
    """Modern Signal CLI interface with upfront configuration collection"""
    
    def __init__(self):
        self.core = None
        self.config = None
        self.ui = ModernCLI()
    
    def show_welcome(self):
        """Show welcome screen"""
        self.ui.print_box("Signal Number Setup", "🚀 Let's set up your Signal number!")
    
    def check_dependencies_upfront(self) -> bool:
        """Check brew tools and signal-cli (install + version) before any CLI-dependent prompts."""
        print(self.ui.section_header("Checking Dependencies", "🔍"))
        
        temp_config = RegistrationConfig(phone_number="+15551112222")  # dummy number for check
        temp_core = SignalCLICore(temp_config)
        
        if not temp_core.check_brew_dependencies():
            print("⚠️  Please install the missing dependencies and run the script again.")
            return False
        
        try:
            temp_core.check_signal_cli()
        except SignalCLINotFoundError as e:
            print()
            print(f"❌ {e}")
            print()
            print("⚠️  Fix the issue above and run the script again.")
            return False
        
        print("✅ All required dependencies are installed (including a compatible signal-cli).")
        return True
    
    def collect_user_configuration(self) -> UserConfig:
        """Collect all user configuration upfront"""
        print(self.ui.section_header("Project Setup"))
        
        # Get operation mode
        print("? What would you like to do?")
        print(self.ui.choice_option("1", "Register new account", "Set up Signal CLI as primary device"))
        print(self.ui.choice_option("2", "Link Signal Desktop", "Add Signal Desktop as secondary device"))
        print()
        
        while True:
            choice = input("  Enter choice (1 or 2) › ").strip()
            if choice == "1":
                mode = "register"
                break
            elif choice == "2":
                mode = "addDevice"
                # Check Signal Desktop status before proceeding
                temp_config = RegistrationConfig(phone_number="+15551112222")  # temporary for check
                temp_core = SignalCLICore(temp_config)
                if temp_core.check_signal_desktop_running():
                    print()
                    print(self.ui.section_header("Signal Desktop Check", "⚠️"))
                    print("Signal Desktop is currently running. For device linking to work properly,")
                    print("Signal Desktop needs to be completely quit first.")
                    print()
                    
                    choice = input("? Automatically quit Signal Desktop? (Y/n) › ").strip().lower()
                    if choice in ['n', 'no']:
                        print("  ❌ Signal Desktop must be quit to proceed with device linking.")
                        print("  Please restart the script after quitting Signal Desktop.")
                        sys.exit(1)
                    
                    print("  ⏳ Quitting Signal Desktop...")
                    if temp_core.quit_signal_desktop():
                        print("  ✅ Signal Desktop quit successfully")
                    else:
                        print("  ❌ Could not quit Signal Desktop automatically")
                        print("     Please quit Signal Desktop manually (Cmd+Q) and restart the script")
                        sys.exit(1)
                break
            else:
                print("  ❌ Please enter 1 or 2")
        
        # Get phone number
        print()
        while True:
            phone_number = input(self.ui.input_prompt(
                "What's your phone number?", 
                "Include country code (e.g., +15551112222)"
            )).strip()
            if phone_number and phone_number.startswith('+') and len(phone_number) > 5:
                break
            print("  ❌ Please enter a valid phone number with country code")
        
        config = UserConfig(phone_number=phone_number, operation_mode=mode)
        
        # Mode-specific questions
        if mode == "register":
            self._collect_registration_config(config)
        elif mode == "addDevice":
            self._collect_device_linking_config(config)
        
        return config
    
    def _collect_registration_config(self, config: UserConfig):
        """Collect registration-specific configuration"""
        print()
        print("📋 Captcha Token Required:")
        print()
        print("Opening captcha page in your browser...")
        
        try:
            import webbrowser
            webbrowser.open("https://signalcaptchas.org/registration/generate.html")
            print("✓ Captcha page opened in browser")
        except Exception as e:
            print(f"⚠️  Could not open browser automatically: {e}")
            print("Please manually open: https://signalcaptchas.org/registration/generate.html")
        
        print()
        print("Steps:")
        print("1. Solve the captcha in your browser")
        print("2. Your existing Signal Desktop app will open, but you should close it")
        print("3. Right click on the 'Open Signal' link and click 'Copy link address'")
        print("4. Come back here when you've copied the link")
        print()
        
        while True:
            ready = input("? Have you copied the captcha token to your clipboard? (y/N) › ").strip().lower()
            
            if ready in ['y', 'yes']:
                # Try to read from clipboard
                try:
                    import subprocess
                    result = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
                    captcha_input = result.stdout.strip()
                    
                    if not captcha_input:
                        print("  ❌ Clipboard is empty. Please copy the captcha token first.")
                        continue
                    
                    print(f"  ✓ Read captcha token from clipboard ({len(captcha_input)} chars)")
                    
                    # Extract token
                    if captcha_input.startswith('signalcaptcha://'):
                        config.captcha_token = captcha_input[len('signalcaptcha://'):]
                    elif 'signalcaptcha://' in captcha_input:
                        start = captcha_input.find('signalcaptcha://') + len('signalcaptcha://')
                        config.captcha_token = captcha_input[start:]
                    else:
                        config.captcha_token = captcha_input
                    break
                        
                except Exception as e:
                    print(f"  ❌ Could not read clipboard: {e}")
                    print("  💡 Please copy the captcha token and try again")
                    continue
            else:
                print("  💡 Please complete the captcha steps above and copy the token")
                continue
        
        print()
        print("? Do you have a registration PIN? (y/N) › ", end="")
        has_pin = input().strip().lower()
        if has_pin in ['y', 'yes']:
            print()
            print("💡 If using Google Voice, check your spam inbox for the PIN")
            config.pin_code = input(self.ui.input_prompt("Enter your PIN")).strip()
    
    def _collect_device_linking_config(self, config: UserConfig):
        """Collect device linking configuration"""
        print()
        
        # Check screen recording permission first
        if QR_UTILS_AVAILABLE:
            has_permission = input("? Have you given your terminal app permission to record your screen? (Y/n) › ").strip().lower()
            
            if has_permission in ['n', 'no']:
                print()
                print("📋 Please grant screen recording permission:")
                print()
                print("1. Open: System Settings > Privacy & Security")
                print("2. Click: Screen & System Audio Recording")
                print("3. Find your terminal app (Terminal, iTerm2, etc.)")
                print("4. Toggle it ON")
                print("5. Restart your terminal app")
                print()
                print("⚠️  The QR code reading feature won't work without this permission")
                print("   (You can still enter the linking URI manually)")
                print()
                input("Press Enter to continue after granting permission › ")
                print()
        
        if not APP_BUILDER_AVAILABLE:
            print("  ⚠️  Signal Desktop app creation not available")
            return
        
        print()
        create_choice = input("? Create a Signal Desktop app launcher? (Y/n) › ").strip().lower()
        config.create_app = create_choice not in ['n', 'no']
        
        if config.create_app:
            print()
            copy_choice = input("? Copy launcher app to Applications folder? (Y/n) › ").strip().lower()
            config.copy_to_applications = copy_choice not in ['n', 'no']
            
            print()
            phone_number_clean = config.phone_number.replace('+', '')
            default_name = f"Signal-{phone_number_clean}"
            app_name = input(self.ui.input_prompt(
                f"App launch name? [Default: {default_name}]", 
                "Leave empty for default, or enter custom name (e.g., work, personal)"
            )).strip()
            
            if app_name:
                config.app_name = app_name

            print()
            print("Launcher icon (Dock / Finder):")
            for i, (_, label) in enumerate(LAUNCHER_ICON_CHOICES, 1):
                print(f"  {i:2}. {label}")
            n_icons = len(LAUNCHER_ICON_CHOICES)
            icon_pick = input(
                f"? Choose icon 1–{n_icons} [1] › "
            ).strip()
            if not icon_pick:
                idx = 0
            else:
                try:
                    n = int(icon_pick)
                    idx = n - 1 if 0 <= n - 1 < n_icons else 0
                except ValueError:
                    idx = 0
            config.launcher_icon_id = LAUNCHER_ICON_CHOICES[idx][0]
    
    def show_configuration_summary(self, config: UserConfig):
        """Show configuration summary before execution"""
        print("\n" + "─" * 60)
        print()
        print("📋 Configuration Summary:")
        print()
        
        mode_names = {"register": "Register new account", "addDevice": "Link Signal Desktop"}
        print(f"   Operation:      {mode_names[config.operation_mode]}")
        print(f"   Phone:          {config.phone_number}")
        
        if config.operation_mode == "register":
            captcha_status = "✓ Yes" if config.captcha_token else "○ No"
            pin_status = "✓ Yes" if config.pin_code else "○ No"
            print(f"   Captcha token:  {captcha_status}")
            print(f"   PIN:            {pin_status}")
        
        if config.operation_mode == "addDevice":
            app_status = "✓ Yes" if config.create_app else "○ No"
            print(f"   Create app:     {app_status}")
            if config.create_app:
                app_name = config.app_name or config.phone_number.replace('+', '')
                copy_status = "✓ Yes" if config.copy_to_applications else "○ No"
                print(f"   Copy to Apps:   {copy_status}")
                print(f"   App name:       Signal-{app_name}")
                print(
                    f"   Launcher icon:  {launcher_icon_label(config.launcher_icon_id)}"
                )
        
        print()
        print("─" * 60)
        print()
        
        confirm = input("? Ready to proceed with this configuration? (Y/n) › ").strip().lower()
        return confirm not in ['n', 'no']
    

    

    def get_verification_code_with_context(self) -> str:
        """Get verification code with context"""
        print(self.ui.section_header("Verification", "📱"))
        print("Check your phone for a 6-digit verification code")
        print("(SMS)")
        print()
        
        while True:
            code = input("? Enter verification code › ").strip()
            if code and len(code) == 6 and code.isdigit():
                return code
            print("  ❌ Please enter a valid 6-digit code")
    
    def get_linking_uri_with_context(self) -> str:
        """Get linking URI with context and automatic QR reading"""
        
        if QR_UTILS_AVAILABLE:
            print("• You'll see a screenshot selector")
            print("• Draw a square around the QR code")
            print()
            
            try:
                qr_data = qr_utils.copy_qr_code_from_screenshot()
                if qr_data and qr_data.startswith('sgnl://linkdevice?'):
                    print("✓ QR code read successfully")
                    return qr_data
                else:
                    print("❌ Could not read QR code, falling back to manual input")
            except Exception as e:
                print(f"❌ QR reading failed: {e}")
        
        print("\nManual URI input:")
        print("1. Copy the linking URI from Signal Desktop")
        print("2. It should start with 'sgnl://linkdevice?'")
        print()
        
        while True:
            uri = input("? Enter linking URI › ").strip()
            
            # Check if input might be truncated (common terminal buffer limit)
            if len(uri) >= 1020 and not uri.endswith('='):
                print("  💡 Input may be truncated. Trying to read from clipboard...")
                try:
                    import subprocess
                    result = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
                    clipboard_content = result.stdout.strip()
                    if clipboard_content and len(clipboard_content) > len(uri):
                        print(f"  ✓ Using clipboard content ({len(clipboard_content)} chars)")
                        uri = clipboard_content
                    else:
                        print("  ⚠️  Clipboard doesn't contain longer text, using typed input")
                except Exception:
                    print("  ⚠️  Could not read clipboard, using typed input")
            
            if uri.startswith('sgnl://linkdevice?'):
                return uri
            print("  ❌ URI should start with 'sgnl://linkdevice?'")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"⚠️  {message}")
    
    def execute_with_progress(self, config: UserConfig):
        """Execute the configuration with clean progress indicators"""
        print(self.ui.section_header("Executing Setup", "⚡"))
        
        if config.operation_mode == "register":
            self._execute_registration(config)
        elif config.operation_mode == "addDevice":
            self._execute_device_linking(config)
    
    def _execute_registration(self, config: UserConfig):
        """Execute registration with progress tracking"""
        steps = [
            "Checking signal-cli installation",
            "Initiating registration",
            "Checking registration status",
            "Verification (if needed)", 
            "Testing setup",
            "Finalizing"
        ]
        
        for i, step in enumerate(steps, 1):
            print(f"{self.ui.progress_step(step, 'in_progress')} ({i}/{len(steps)})", end='', flush=True)
            
            try:
                if step == "Checking signal-cli installation":
                    self.config = RegistrationConfig(phone_number=config.phone_number)
                    self.core = SignalCLICore(self.config)
                    self.core.check_signal_cli()
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Initiating registration":
                    self.core.register_sms(config.captcha_token)
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Checking registration status":
                    # Check if device is already registered after captcha submission
                    config.needs_verification = not self.core.verify_account_registered()
                    if config.needs_verification:
                        print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)}) - SMS verification needed")
                    else:
                        print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)}) - already registered")
                
                elif step == "Verification (if needed)":
                    if hasattr(config, 'needs_verification') and config.needs_verification:
                        if not config.verification_code:
                            print()  # Add newline before verification section
                            config.verification_code = self.get_verification_code_with_context()
                        self.core.verify_registration(config.verification_code, config.pin_code)
                        print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                    else:
                        print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)}) - skipped")
                
                elif step == "Testing setup":
                    if self.core.test_registration():
                        pass  # Silent success
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Finalizing":
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
            except Exception as e:
                print(f"\r{self.ui.progress_step(step, 'failed')} ({i}/{len(steps)})")
                raise e
        
        self._show_registration_success(config)
    
    def _execute_device_linking(self, config: UserConfig):
        """Execute device linking with progress tracking"""
        steps = [
            "Checking signal-cli installation",
            "Verifying account registration",
            "Creating Signal Desktop app" if config.create_app else None,
            "Launching Signal Desktop",
            "Reading QR code",
            "Linking device",
            "Syncing data",
            "Finalizing"
        ]
        steps = [s for s in steps if s is not None]  # Remove None steps
        
        created_app_name = None
        
        for i, step in enumerate(steps, 1):
            print(f"{self.ui.progress_step(step, 'in_progress')} ({i}/{len(steps)})", end='', flush=True)
            
            try:
                if step == "Checking signal-cli installation":
                    self.config = RegistrationConfig(phone_number=config.phone_number)
                    self.core = SignalCLICore(self.config)
                    self.core.check_signal_cli()
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Verifying account registration":
                    if not self.core.verify_account_registered():
                        raise SignalRegistrationError(
                            f"Account {config.phone_number} is not registered. "
                            "Please run registration first."
                        )
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Creating Signal Desktop app":
                    app_config = AppConfig(
                        phone_number=config.phone_number,
                        app_name=config.app_name,
                        output_dir=None,
                        launcher_icon_id=config.launcher_icon_id,
                    )
                    # Suppress verbose output from app creation
                    import sys
                    from io import StringIO
                    old_stdout = sys.stdout
                    sys.stdout = StringIO()
                    try:
                        app_path, created_app_name = self.core.create_signal_app(app_config)
                    finally:
                        sys.stdout = old_stdout
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                    print(f"  • Created: {created_app_name}")
                
                elif step == "Launching Signal Desktop":
                    user_data_dir = self.core.launch_signal_desktop()
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Reading QR code":
                    print()  # Add newline before QR section
                    link_uri = self.get_linking_uri_with_context()
                    print(f"{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Linking device":
                    self.core.link_device_to_signal_cli(link_uri)
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Syncing data":
                    self.core.sync_signal_data()
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
                elif step == "Finalizing":
                    if created_app_name and config.copy_to_applications:
                        print("  • Copying app to Applications...")
                        if self.core.copy_app_to_applications(created_app_name):
                            print(f"  • {created_app_name} copied to Applications")
                        else:
                            print(f"  • Could not copy automatically")
                    print(f"\r{self.ui.progress_step(step, 'completed')} ({i}/{len(steps)})")
                
            except Exception as e:
                print(f"\r{self.ui.progress_step(step, 'failed')} ({i}/{len(steps)})")
                raise e
        
        self._show_device_linking_success(config, created_app_name)
    
    def _show_registration_success(self, config: UserConfig):
        """Show registration success message and optionally continue with Signal Desktop setup"""
        self.ui.print_box("Success!", "✅ Signal CLI registered successfully!")
        print()
        print("🎯 What's next?")
        print()
        print(f"   signal-cli -a {config.phone_number} receive    # Check messages")
        print(f"   signal-cli -a {config.phone_number} daemon     # Run continuously")
        print()
        print("💾 Account data stored in: ~/.local/share/signal-cli/data/")
        print()
        
        self._offer_install_receive_job(config.phone_number)
        print()
        
        # Ask if they want to set up Signal Desktop
        try:
            setup_desktop = input("? Would you like to set up Signal Desktop now? (Y/n) › ").strip().lower()
            
            if setup_desktop not in ['n', 'no']:
                print()
                print("🔄 Continuing with Signal Desktop setup...")
                
                # Create device linking config
                device_config = UserConfig(
                    phone_number=config.phone_number,
                    operation_mode="addDevice"
                )
                
                # Collect device linking configuration
                self._collect_device_linking_config(device_config)
                
                # Show configuration summary for device linking
                if not self.show_configuration_summary(device_config):
                    print("✅ Signal Desktop setup cancelled. You can run this script again with 'addDevice' mode later.")
                    return
                
                # Execute device linking
                try:
                    self._execute_device_linking(device_config)
                except Exception as e:
                    print(f"\n❌ Signal Desktop setup failed: {e}")
                    print("✅ Registration is still complete! You can run this script again with 'addDevice' mode later.")
            else:
                print("✅ Registration complete! You can run this script again with 'addDevice' mode to set up Signal Desktop later.")
                
        except KeyboardInterrupt:
            print("\n✅ Registration complete! You can run this script again with 'addDevice' mode to set up Signal Desktop later.")
        except Exception as e:
            print(f"\n⚠️  Error during Signal Desktop setup: {e}")
            print("✅ Registration is still complete! You can run this script again with 'addDevice' mode later.")
    
    def _show_device_linking_success(self, config: UserConfig, created_app_name: Optional[str]):
        """Show device linking success message"""
        self.ui.print_box("Success!", "✅ Signal Desktop linked successfully!")
        print()
        print("🎯 What's next?")
        print()
        if created_app_name:
            if config.copy_to_applications:
                print(f"   • Launch {created_app_name} from Applications")
                print("   • Add to Dock for quick access")
            else:
                print(f"   • Drag {created_app_name} to Applications folder")
                print("   • Launch it anytime for Signal Desktop")
        else:
            print("   • Use Signal Desktop normally")
        print("   • You need to specify a profile display name in Signal Desktop settings so people know who is messaging them. This doesn't need to be your real name.")
        print("   • Turn on disappearing messages by *default* (in Signal settings)")
        print("   • Set a Signal username so you don't have to give out this phone number: https://support.signal.org/hc/en-us/articles/6712070553754-Phone-Number-Privacy-and-Usernames")
        print("   • Optionally disable 'discover by phone number' for even more privacy")
        print("   • Set a Signal PIN so no one else can register with this number")
        
        print()
        self._offer_install_receive_job(config.phone_number)
    
    def _offer_install_receive_job(self, phone_number: str):
        """
        Offer to install a launchd job that runs `signal-cli receive` on a schedule.
        """
        if needs_receive_job_repair(phone_number):
            print(
                "⚠️  LaunchAgent plist exists but the receive script is missing "
                f"under ~/Library/Application Support/signal-voip-registration-helper/\n"
                "   Re-run install to recreate it (safe):"
            )
            try:
                fix = input(
                    "? Repair now (recreate script and reload job)? (Y/n) › "
                ).strip().lower()
                if fix in ("n", "no"):
                    print(
                        f"   Run later: python3 signal_voip_helper.py installReceiveJob {phone_number}"
                    )
                    return
                ok, msg = install_receive_job(phone_number)
                if ok:
                    print("✅ Repaired: script recreated and job reloaded.")
                    print(f"   {msg}")
                else:
                    print(f"⚠️  {msg}")
                return
            except KeyboardInterrupt:
                print()
                return

        if is_receive_job_installed(phone_number):
            print(
                "ℹ️  A daily background job is already installed for this number "
                "(signal-cli receive). To remove it later, run:\n"
                f"   python3 signal_voip_helper.py uninstallReceiveJob {phone_number}"
            )
            return
        try:
            choice = input(
                "? Install a daily background job to fetch messages with signal-cli "
                "(recommended — keeps encryption/session healthy)? (Y/n) › "
            ).strip().lower()
            if choice in ("n", "no"):
                print(
                    "   You can install it later with:\n"
                    f"   python3 signal_voip_helper.py installReceiveJob {phone_number}"
                )
                return
            ok, msg = install_receive_job(phone_number)
            if ok:
                print("✅ Background job installed.")
                print(f"   LaunchAgent: {msg}")
                print(
                    "   It runs at login and about twice per day while you are logged in "
                    "(see README). Logs: ~/Library/Logs/signal-voip-registration-helper/"
                )
            else:
                print(f"⚠️  Could not install the scheduled job:\n{msg}")
        except KeyboardInterrupt:
            print()
            print(
                f"   Skipped. Install later: python3 signal_voip_helper.py installReceiveJob {phone_number}"
            )
    
    def run_modern_wizard(self):
        """Run the modern wizard with upfront configuration collection"""
        self.show_welcome()
        
        # Check dependencies before proceeding
        if not self.check_dependencies_upfront():
            sys.exit(1)
        
        # Collect all configuration upfront
        config = self.collect_user_configuration()
        
        # Show summary and confirm
        if not self.show_configuration_summary(config):
            print("❌ Setup cancelled")
            return
        
        try:
            # Execute with progress indicators
            self.execute_with_progress(config)
            
        except (SignalCLINotFoundError, RegistrationFailedError, 
                VerificationFailedError, DeviceLinkingError, 
                SignalRegistrationError) as e:
            print(f"\n❌ {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n❌ Setup cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            sys.exit(1)
    
    def run_with_params(self, mode: str, phone_number: str, captcha_token: Optional[str] = None, 
                       device_name: str = "signal-cli-desktop"):
        """Run with command line parameters - using modern flow"""
        # Check dependencies first
        if not self.check_dependencies_upfront():
            sys.exit(1)
        
        # Create a UserConfig from the parameters
        config = UserConfig(
            phone_number=phone_number,
            operation_mode=mode,
            captcha_token=captcha_token,
            device_name=device_name
        )

        
        if mode == "register" and not config.captcha_token:
            print("❌ Error: Captcha token is required for registration")
            sys.exit(1)
        
        try:
            # Execute with our modern progress system
            self.execute_with_progress(config)
            
        except (SignalCLINotFoundError, RegistrationFailedError, 
                VerificationFailedError, DeviceLinkingError, 
                SignalRegistrationError) as e:
            print(f"❌ {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
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
  python3 signal_voip_helper.py register +15551112222 --captcha <token>

  # Add Signal Desktop as linked device (addDevice)
  # Automatically reads QR code from screenshot, or manual URI input
  python3 signal_voip_helper.py addDevice +15551112222

  # Install / remove macOS daily signal-cli receive job (after registration)
  python3 signal_voip_helper.py installReceiveJob +15551112222
  python3 signal_voip_helper.py uninstallReceiveJob +15551112222

Note: For captcha tokens, you can:
1. Paste the full line from the browser console
2. Paste just the token part
        """
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        choices=[
            'register',
            'addDevice',
            'installReceiveJob',
            'uninstallReceiveJob',
        ],
        help='Operation mode (register, addDevice, or install/uninstall daily receive job)',
    )
    parser.add_argument('phone_number', nargs='?', 
                       help='Phone number in international format (e.g., +15551112222)')
    parser.add_argument('--captcha', help='Captcha token for registration')
    parser.add_argument('--pin', help='Registration PIN (deprecated - will be prompted interactively)')
    parser.add_argument('--device-name', default='signal-cli-desktop',
                       help='Device name for linking (default: signal-cli-desktop)')
    
    args = parser.parse_args()
    
    interface = SignalCLIInterface()
    
    # If no arguments provided, run wizard mode
    if not args.mode:
        interface.run_modern_wizard()
        return
    
    # Parameter mode
    if not args.phone_number:
        print("❌ Error: Phone number is required for parameter mode")
        parser.print_help()
        sys.exit(1)

    if args.mode == "installReceiveJob":
        if needs_receive_job_repair(args.phone_number):
            print(
                "Repairing: LaunchAgent plist exists but receive script was missing; "
                "recreating script…",
                file=sys.stderr,
            )
        ok, msg = install_receive_job(args.phone_number)
        if ok:
            print("✅ Daily receive job installed.")
            print(f"   {msg}")
            print(
                "   Script: ~/Library/Application Support/signal-voip-registration-helper/"
            )
            print("   Logs: ~/Library/Logs/signal-voip-registration-helper/")
        else:
            print(f"❌ {msg}")
        sys.exit(0 if ok else 1)

    if args.mode == "uninstallReceiveJob":
        ok, msg = uninstall_receive_job(args.phone_number)
        print(msg if ok else f"❌ {msg}")
        sys.exit(0 if ok else 1)
    
    interface.run_with_params(
        args.mode,
        args.phone_number,
        args.captcha,
        args.device_name,
    )


if __name__ == "__main__":
    main()
