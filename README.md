# TikTok Profile Scraper

A production-ready Python script to scrape TikTok profiles using Playwright with captcha solving capabilities.

## Features

- 🚀 **Asynchronous execution** using `asyncio` and Playwright
- 🔐 **Captcha solving** using SadCaptcha API with manual fallback
- 🌐 **Proxy support** with authentication and SSL handling
- 🎭 **User-Agent rotation** for anti-bot evasion
- 📊 **Complete video data extraction** (views, likes, comments, shares, timestamps)
- 🛡️ **Robust error handling** with comprehensive logging
- 📁 **Clean JSON output** with timestamped filenames

## Requirements

- Python 3.10+
- SadCaptcha API key (optional, for automatic captcha solving)
- Proxy credentials (optional, for enhanced anonymity)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tiktok-scraper.git
cd tiktok-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

## Configuration

### SadCaptcha API Key (Optional)
1. Sign up at [SadCaptcha](https://www.sadcaptcha.com/dashboard)
2. Set your API key as an environment variable:
```bash
export SADCAPTCHA_API_KEY="your_api_key_here"
```
Or modify the `SADCAPTCHA_API_KEY` variable in `main.py`

### Proxy Configuration (Optional)
Edit the proxy settings in `main.py`:
```python
PROXY_HOST = "your-proxy-host.com"
PROXY_PORT = 8080
PROXY_USERNAME = "your_username"
PROXY_PASSWORD = "your_password"
```

## Usage

### Basic Usage
```bash
python3 main.py tiktok
```

### Custom Username
```bash
python3 main.py username_here
```

### Example Output
The script will create a JSON file with the latest 5 videos:
```json
[
  {
    "id": "7546692323917319455",
    "desc": "brb watching every single 'Show Me Love' video on my feed @wizthemc #BehindTheBreakthrough",
    "views": 262700,
    "likes": 2454,
    "comments": 1703,
    "shares": 193,
    "created": "2025-09-05T19:40:54"
  }
]
```

## How It Works

1. **Browser Automation**: Uses Playwright to navigate to TikTok profiles
2. **API Interception**: Captures TikTok's internal API responses for video data
3. **Captcha Handling**: Automatically detects and solves captchas using SadCaptcha API
4. **Data Extraction**: Extracts the first 5 videos as they appear on the profile page
5. **Output Generation**: Saves results to timestamped JSON files

## Anti-Bot Features

- **User-Agent Rotation**: Cycles through realistic Chrome desktop user agents
- **Proxy Support**: Routes traffic through proxy servers with authentication
- **SSL Handling**: Bypasses SSL certificate validation for proxy compatibility
- **Human-like Behavior**: Includes scrolling interactions and realistic delays
- **Captcha Solving**: Handles TikTok's security challenges automatically

## Error Handling

The script includes comprehensive error handling for:
- Network connectivity issues
- Captcha solving failures
- Empty API responses
- Browser crashes
- Proxy authentication errors

## Logging

All operations are logged with timestamps and severity levels:
- **INFO**: Normal operation status
- **WARNING**: Non-critical issues (empty responses, fallback usage)
- **ERROR**: Critical errors with detailed stack traces

## Legal Notice

This tool is for educational purposes only. Please respect TikTok's Terms of Service and rate limits. Use responsibly and ensure compliance with applicable laws and regulations.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 