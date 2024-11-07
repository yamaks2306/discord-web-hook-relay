# Discord Webhook Relay

A serverless function that relays messages to Discord webhooks with different severity levels (warning/critical).

## Overview

This service provides an API endpoint that accepts JSON payloads and forwards them to Discord webhooks. It supports two severity levels:
- Warning (yellow color)
- Critical (red color)

The service automatically adds appropriate colors to the Discord embeds based on the severity level.

## API Usage

### Authentication

All requests must include an API key in the `X-API-Key` header. Requests without a valid API key will receive a 401 Unauthorized response.

### Request Format

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "content": "Optional message text",
    "embeds": [{
      "title": "Alert Title",
      "description": "Alert description",
      "fields": [
        {
          "name": "Field Name",
          "value": "Field Value",
          "inline": false
        }
      ]
    }]
  }' \
  https://your-domain/api/warning  # or /critical
```

### Endpoints

- `/warning` - for warning messages (yellow)
- `/critical` - for critical messages (red)

### Request Format

- `content` (optional): String message that appears above the embed
- `embeds`: Array of embed objects (currently only the first embed is processed)
  - `title` (optional): Embed title
  - `description` (optional): Embed description
  - `fields` (optional): Array of field objects
    - `name`: Field name
    - `value`: Field value
    - `inline`: Boolean, whether the field should be inline

Note: At least one of `title`, `description`, or `fields` must be present in the embed.

### Response Codes

- 200: Message successfully sent
- 400: Invalid request (missing required fields or invalid format)
- 500: Server error or Discord API error

### Example Response

Success:
```json
{
    "message": "Webhook successfully sent (warning)",
    "level": "warning"
}
```

Error:
```json
{
    "error": "Embed must contain at least one of the fields: title, description or fields"
}
```

## Environment Variables

The following environment variables must be set:
- `API_KEY`: Secret key for authenticating requests
- `DISCORD_WEBHOOK_URL_WARNING`: Discord webhook URL for warning messages
- `DISCORD_WEBHOOK_URL_CRITICAL`: Discord webhook URL for critical messages

## Deployment

### Prerequisites

1. Digital Ocean account with Functions enabled
2. [doctl](https://docs.digitalocean.com/reference/doctl/how-to/install/) CLI tool installed
3. Discord webhook URLs for both warning and critical levels

### Environment Setup

1. Create a `.env` file with the following variables:
```bash
API_KEY=your-secret-api-key
DISCORD_WEBHOOK_URL_WARNING=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_URL_CRITICAL=https://discord.com/api/webhooks/...
```

2. Connect to your Digital Ocean account:
```bash
doctl auth init
doctl serverless install
```

### Deployment Steps

1. Create a new namespace if you don't have one and connect to it:
```bash
# Digital Ocean api slugs: https://slugs.do-api.dev
doctl serverless namespaces create --label discord-webhook-relay --region <region slug>
doctl serverless namespaces list
doctl serverless connect
```

2. Deploy the function:
```bash
doctl serverless deploy . --env .env --remote-build
```

3. Get the deployment URL:
```bash
doctl serverless functions get discord-webhook-relay/send
```

### Testing the Deployment

Test the warning endpoint:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "content": "Test message",
    "embeds": [{
      "title": "Test Alert",
      "description": "This is a test alert"
    }]
  }' \
  https://your-deployment-url/warning
```

### Updating the Function

To update the deployed function:
```bash
doctl serverless deploy . --env .env --remote-build
```

### Monitoring and Logs

View function logs:
```bash
doctl serverless activations logs
```

List recent activations:
```bash
doctl serverless activations list
```

## Development

The service is built using:
- Python 3.x
- Pydantic for request validation
- Requests library for HTTP calls