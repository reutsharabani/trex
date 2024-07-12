# Trex Bot

Trex is a simple bot designed to monitor changes in URLs, named after the unique vision of a T-Rex that detects movement.
It aims to track updates on websites with dynamic content.

## Features

- **Dynamic Content Tracking**: Fetches webpage content and snapshots, supports JS dependant sites (using pyppeteer).
- **Scheduled Checks**: Periodically checks tracked URLs for changes.
- **Slack Integration**: Responds to commands and uploads images directly in Slack.

## Prerequisites

- Python 3.8 or newer
- Pip for Python package management

## Installation

   ```bash
   # Clone the repository:
   git clone https://github.com/yourrepo/trex.git
   # Navigate to the project directory:
   cd trex
   # Install dependencies:
   pip install -r requirements.txt
   ```

## Usage

After setting up the bot, you can use the following slash commands in Slack:

- `/track <url>`: Start tracking a URL.
- `/untrack <url>`: Stop tracking a URL.
- `/tracks`: List all tracked URLs and their status.
- `/visit <url>`: Mark a URL as visited (unchanged).
- `/show <url>`: Display the last captured image of the URL.
- `/next-run`: Check when the next check for changes is scheduled.
- `/run-now`: Immediately check all tracked URLs for changes.

## Configuration

Set the following environment variables with your Slack app's credentials:

```bash
PYPPETEER_CHROMIUM_REVISION=1326920 # Adjust as necessary
SLACK_APP_TOKEN=xapp-****...
SLACK_BOT_TOKEN=xoxb-****...
```

## Bot Permissions

Ensure your Slack app has the following permissions for full functionality (may need less, didn'y bother checking):

- `chat:write`: Send responses.
- `chat:write.public`: Post images in channels.
- `commands`: Use slash commands.
- `files:write`: Upload files.
- `im:read`: Respond to direct messages.

## Troubleshooting

If you encounter issues, check the following:

- Ensure all environment variables are correctly set.
- Verify that your Slack app has the necessary permissions.

## Contributing

Contributions are welcome! Please submit pull requests or open issues for any enhancements, bug fixes, or features.

## License

1. Do whatever you want with the code.
2. I am not responsible for ANYTHING that may happen as a result of using this code.
