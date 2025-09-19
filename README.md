# Signal VOIP Registration Script

A helper script for registering new Signal accounts **without a phone** and linking to Signal Desktop. Only works for macOS.

This script was designed to help with the workflow of registering Google Voice or other VOIP numbers that are not working on a physical phone and attaching them to unique Signal Desktop instances, so you can run multiple Signal numbers from one profile.

**Warning:** This tool is new and hasn't been tested for long-term use. Please report bugs you encounter.

Don't use this to spam people.

## Who is this for?

**This is for you if:**

* You want to run multiple Signal accounts from your computer
* You don't want to have to buy another phone just to run another Signal account
* You don't need this Signal account to also be attached to a physical phone
* You want a free/cheap Signal account

**This tool is not for you if:**

* You already have your Signal account registered to a physical phone. (I made a guide for just [creating a second Signal Desktop instance when you already have a phone as your primary device](https://github.com/blanchardjeremy/signal-voip-registration-helper/wiki/How-to-run-multiple-Signal-Desktop-instances-on-macOS)).

## Features

* **New Account Registration**: Register a new Signal account (without needing a physical phone). The primary "device" is actually just the [`signal-cli`](https://github.com/AsamK/signal-cli) library on your computer. However, after you link it to a Signal Desktop instance, you won't need to use `signal-cli` again.
* **Link Signal Desktop**: Link Signal Desktop as a [secondary device](https://support.signal.org/hc/en-us/articles/360007320551-Linked-Devices)
* **QR Code support**: Helps you scan the QR code during the Signal Desktop linking process. This is useful because that process is built for linking a phone where you can scan the code with your phone camera. In this case, our computer is the primary device, so it's a little cumbersome to get the data within the QR code.
* **Application launcher**: Create a launcher that opens a unique instance of Signal Desktop for each account you register

## Installation

1. Clone or download this repository

   ```bash
   git clone https://github.com/blanchardjeremy/signal-voip-registration-helper
   cd signal-voip-registration-helper
   ```

2. Install dependencies via Homebrew: (Make sure to [install Homebrew](https://brew.sh/) first)

   ```bash
   brew install signal-cli zbar
   ```

## Usage

### First, get a VOIP number

You do need a real phone number, but you don't need a standard phone or mobile carrier (SIM or eSIM). It is helpful to get a number you control long-term so that you don't lose access to the Signal account in case you ever need to re-verify it.

**Where you can get a VOIP number:**

_Note:_ These won't be anonymous numbers since your identity is required to set up each account.

* [Google Voice](https://workspace.google.com/products/voice/) - free - Your number will expire if you don't send a text or make a call once every 3 months. (From Google Voice, not from Signal.)
* [MySudo](https://anonyome.com/individuals/mysudo/) - $2/mo for 1 number, $15/mo for 9 numbers

**Less-reliable options for getting a VOIP number:**

> [!WARNING]
> Use the options below with caution because you only control this number temporarily and there is a chance it can be registered by someone else in the future. The way to ensure you maintain control is to A) set a [Signal PIN](https://support.signal.org/hc/en-us/articles/360007059792-Signal-PIN) and enable Signal's [registration lock](https://support.signal.org/hc/en-us/articles/360007059792-Signal-PIN#manage_registration_lock) feature and B) check the messages on this number at least once every 7 days. If you do both of those things, you should maintain control.

* [SMSPool](https://smspool.net/) - $0.20 per registration - Much cheaper to use if you need to register many accounts. For increased anonymity, you can purchase using Monero and access the site through Tor.

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
```

#### Link Signal Desktop as Secondary Device

```bash
./signal_voip_helper.py addDevice +15551112222
```

### Getting Captcha Tokens

1. Open <https://signalcaptchas.org/registration/generate.html> in your browser
2. Solve the captcha
3. Right click on the "Open Signal" link and click "Copy link address"
4. Paste the link address into the prompt

## Troubleshooting

1. **"signal-cli is not installed or not in PATH"**
   * Install `signal-cli` following the instructions above
   * Ensure it's in your system PATH

2. **Verification code not received**
   * Check your phone for SMS
   * Ensure your phone number is correct

3. **Device linking fails**
   * Make sure the QR code hasn't expired
   * Verify the linking URI starts with `sgnl://linkdevice?`
   * Ensure you're running from the correct signal-cli account

## Security Notes

* Phone numbers and verification codes should be kept private
* The script stores no sensitive data locally
* No data is sent off your machine (except to interact directly with Signal's servers, of course)
* All Signal data is stored in `~/.local/share/signal-cli/data/`

## License

See [LICENSE.txt](./LICENSE.txt) for license details.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this script.
