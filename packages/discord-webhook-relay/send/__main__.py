from typing import Dict, Any, Optional, List
from pydantic import BaseModel, HttpUrl
import requests
import os
import json
import base64

# Discord webhook models
class EmbedField(BaseModel):
    name: str
    value: str
    inline: Optional[bool] = False

class EmbedFooter(BaseModel):
    text: str
    icon_url: Optional[HttpUrl] = None

class EmbedImage(BaseModel):
    url: HttpUrl

class EmbedAuthor(BaseModel):
    name: str
    url: Optional[HttpUrl] = None
    icon_url: Optional[HttpUrl] = None

class Embed(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[HttpUrl] = None
    color: Optional[int] = None
    fields: Optional[List[EmbedField]] = None
    footer: Optional[EmbedFooter] = None
    image: Optional[EmbedImage] = None
    author: Optional[EmbedAuthor] = None

class DiscordWebhook(BaseModel):
    content: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    tts: Optional[bool] = False
    embeds: Optional[List[Embed]] = None

    class Config:
        extra = "forbid"

def validate_api_key(headers: Dict[str, str]) -> bool:
    """Check API key from headers"""
    expected_key = os.environ.get('API_KEY')
    if not expected_key:
        return False
    
    # Getting the key from the X-API-Key header
    provided_key = headers.get('x-api-key')
    return provided_key == expected_key

def get_webhook_url(path: str) -> Optional[str]:
    """Get webhook URL based on the path"""
    path = path.strip('/')
    if path == 'warning':
        return os.environ.get('DISCORD_WEBHOOK_URL_WARNING')
    elif path == 'critical':
        return os.environ.get('DISCORD_WEBHOOK_URL_CRITICAL')
    return None

def main(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Constructing the request body from the root of args
        body = {
            "content": args.get("content"),
            "embeds": args.get("embeds", [])
        }
        
        # Add color based on the importance level
        if not body.get('embeds'):
            body['embeds'] = [{}]
            
        path = args.get('__ow_path', '').strip('/')
        body['embeds'][0]['color'] = 16776960 if path == 'warning' else 16711680

        # Check if there is any content in the first embed
        if not any([
            body['embeds'][0].get('title'),
            body['embeds'][0].get('description'),
            body['embeds'][0].get('fields')
        ]):
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Embed must contain at least one of the fields: title, description or fields"
                })
            }

        # Validate data using Pydantic
        try:
            webhook_data = DiscordWebhook(**body)
        except Exception as e:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Validation error: {str(e)}"
                })
            }

        # Getting webhook URL
        webhook_url = get_webhook_url(path)
        if not webhook_url:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid webhook path"})
            }

        # Send data to Discord
        try:
            response = requests.post(
                webhook_url,
                json=webhook_data.dict(exclude_none=True)
            )
            
            if not response.ok:
                error_details = response.json() if response.content else "No error details"
                return {
                    "statusCode": response.status_code,
                    "body": json.dumps({
                        "error": f"Discord returned an error: {response.status_code}",
                        "details": error_details
                    })
                }
                
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Error sending webhook: {str(e)}"})
            }

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Webhook successfully sent ({path})",
                "level": path
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"})
        }
