# Signal CLI Registration Script

A Python script for registering new Signal accounts and linking devices using the Signal CLI tool.

## Features

- **New Account Registration**: Register a new Signal account as a primary device
- **Device Linking**: Link Signal Desktop as a secondary device to an existing signal-cli account
- **Interactive Wizard**: User-friendly command-line interface
- **Captcha Support**: Handles Signal's captcha verification process
- **SMS/Voice Verification**: Supports both SMS and voice call verification methods
- **Command Line Interface**: Can be run with parameters for automation

## Prerequisites

### Required Software

1. **Python 3.6+** (Python 3.9.5 recommended)
2. **signal-cli** - Command line interface for Signal messaging

### Installing signal-cli

Download the latest release from: <https://github.com/AsamK/signal-cli/releases/latest>

For macOS:

```bash
# Using Homebrew
brew install signal-cli
```

## Installation

1. Clone or download this repository
2. Ensure `signal-cli` is installed and accessible in your PATH
3. Make the script executable (optional):

   ```bash
   chmod +x register-number.py
   ```

## Usage

### Interactive Wizard Mode (Recommended for first-time users)

```bash
python3 register-number.py
```

This will guide you through the setup process step by step.

### Command Line Mode

#### Register New Account

```bash
# With captcha token
python3 register-number.py register +1234567890 --captcha <token>

# With captcha token from file (recommended for long tokens)
python3 register-number.py register +1234567890 --captcha-file captcha.txt
```

#### Link Signal Desktop as Secondary Device

```bash
python3 register-number.py addDevice +1234567890
```

## Getting Captcha Tokens

1. Open <https://signalcaptchas.org/registration/generate.html> in your browser
2. Open Developer Tools (F12)
3. Go to Console tab
4. Solve the captcha
5. Look for a line like: `'Launched external handler for "signalcaptcha://..."'`
6. Copy the entire line or just the token part

**Tip**: For very long captcha tokens, save them to a file and use the `--captcha-file` option.

## Examples

### Complete Registration Flow

```bash
# 1. Run interactive wizard
python3 register-number.py

# 2. Choose option 1 (New account registration)
# 3. Enter phone number
# 4. Follow captcha instructions
# 5. Enter verification code
# 6. Complete setup
```

### Linking Signal Desktop

```bash
# 1. Run addDevice mode
python3 register-number.py addDevice +1234567890

# 2. Follow instructions to scan QR code from Signal Desktop
# 3. Enter the linking URI
# 4. Complete device linking
```

## File Structure

```txt
signal-registration-cli/
├── register-number.py    # Main script
├── requirements.txt      # Dependencies documentation
├── README.md            # This file
└── qr_utils.py          # QR code utilities (if present)
```

## Dependencies

### Python Dependencies

All required Python modules are part of the standard library:

- `argparse` - Command line argument parsing
- `subprocess` - Running external commands
- `sys` - System-specific parameters
- `time` - Time-related functions
- `typing` - Type hints
- `os` - Operating system interface

### External Dependencies

- **signal-cli** - Must be installed separately (see Prerequisites section)

## Troubleshooting

### Common Issues

1. **"signal-cli is not installed or not in PATH"**
   - Install signal-cli following the instructions above
   - Ensure it's in your system PATH

2. **Verification code not received**
   - Check your phone for SMS or voice call
   - Wait up to 60 seconds for voice verification
   - Ensure your phone number is correct

3. **Device linking fails**
   - Make sure the QR code hasn't expired
   - Verify the linking URI starts with `sgnl://linkdevice?`
   - Ensure you're running from the correct signal-cli account

### Getting Help

- Check that `signal-cli` is working: `signal-cli --version`
- Verify your phone number format: `+1234567890`
- Ensure you have a stable internet connection

## Security Notes

- Captcha tokens are temporary and expire quickly
- Phone numbers and verification codes should be kept private
- The script stores no sensitive data locally
- All Signal data is stored in `~/.local/share/signal-cli/data/`

## License

This script is provided as-is for educational and personal use. Please ensure you comply with Signal's terms of service and applicable laws when using this tool.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this script.
