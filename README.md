# Signal CLI Registration Script

A helper script for registering new Signal accounts and linking to Signal Desktop. macOS support.

This script was designed to help with the workflow of registering Google Voice or other VOIP numbers and attaching them to unique Signal Desktop instances, so you can run multiple Signal numbers from one profile.

**Warning:** This tool is new and hasn't been tested for long-term use. Please report bugs you encounter.

Don't use this to spam people.

## Features

- **New Account Registration**: Register a new Signal account as a primary device. The primary "device" is signal-cli on your computer. Though you don't need to ever interact with it that way after you add it to the desktop.
- **Link Signal Desktop**: Link Signal Desktop as a secondary device to an existing signal-cli account
- **Captcha Support**: Handles Signal's captcha verification process

## Installation

1. Clone or download this repository

   ```bash
   git clone https://github.com/blanchardjeremy/signal-voip-registration-helper
   ```

2. Install dependencies via Homebrew:

   ```bash
   brew install signal-cli zbarimg
   ```

## Usage

## Step 1: Get a VOIP number

You do need a real phone number, but you don't need a standard phone or mobile carrier (SIM or eSIM). It is helpful to get a number you control long-term so that you don't lose access to the Signal account in case you ever nee dto re-verify it.

**Where you can get a VOIP number:**

- [Google Voice](https://workspace.google.com/products/voice/) - free - Your number will expire if you don't send a text or make a call once every 3 months. (From Google Voice, not from Signal.)
- [MySudo](https://anonyome.com/individuals/mysudo/) - $2/mo for 1 number, $15/mo for 9 numbers

### Interactive Wizard Mode (Recommended)

```bash
./signal_voip_helper.py
```

This will guide you through the setup process step by step.

### Command Line Mode

#### Register New Account

```bash
# With captcha token
./signal_voip_helper.py register +15551112222 --captcha <token>

# With captcha token from file (recommended for long tokens)
./signal_voip_helper.py register +15551112222 --captcha-file captcha.txt
```

#### Link Signal Desktop as Secondary Device

```bash
./signal_voip_helper.py addDevice +15551112222
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
./signal_voip_helper.py

# 2. Choose option 1 (New account registration)
# 3. Enter phone number
# 4. Follow captcha instructions
# 5. Enter verification code
# 6. Complete setup
```

### Linking Signal Desktop

```bash
# 1. Run addDevice mode
./signal_voip_helper.py addDevice +15551112222

# 2. Follow instructions to scan QR code from Signal Desktop
# 3. Enter the linking URI
# 4. Complete device linking
```

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

## Security Notes

- Phone numbers and verification codes should be kept private
- The script stores no sensitive data locally
- All Signal data is stored in `~/.local/share/signal-cli/data/`

## License

This script is provided as-is for educational and personal use. Please ensure you comply with Signal's terms of service and applicable laws when using this tool.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this script.
