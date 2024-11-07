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

def validate_api_key(path: str) -> bool:
    """Check API key from path"""
    expected_key = os.environ.get('API_KEY')
    if not expected_key:
        return False
    
    # Extract API key from path
    path_parts = path.strip('/').split('/')
    if len(path_parts) < 2:
        return False
        
    provided_key = path_parts[-2]
    return provided_key == expected_key

def get_webhook_url(path: str) -> Optional[str]:
    """Get webhook URL based on the path"""
    path_parts = path.strip('/').split('/')
    if len(path_parts) < 2:
        return None
        
    # Use the last part of the path for webhook type
    webhook_type = path_parts[-1]
    if webhook_type == 'warning':
        return os.environ.get('DISCORD_WEBHOOK_URL_WARNING')
    elif webhook_type == 'critical':
        return os.environ.get('DISCORD_WEBHOOK_URL_CRITICAL')
    return None

def main(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        path = args.get('__ow_path', '').strip('/')
        path_parts = path.strip('/').split('/')
        
        # Check if debug mode is enabled (defaults to False)
        debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
        
        debug_info = {
            "original_path": path,
            "path_parts": path_parts,
            "api_key_from_path": path_parts[-2] if len(path_parts) >= 2 else None,
            "webhook_type": path_parts[-1] if len(path_parts) >= 1 else None,
            "expected_api_key": None, # os.environ.get('API_KEY'),
            "webhook_url": None
        }

        if not validate_api_key(path):
            return {
                "statusCode": 401,
                "body": json.dumps({
                    "error": "Invalid or missing API key",
                    "debug": debug_info if debug_mode else None
                })
            }

        webhook_url = get_webhook_url(path)
        debug_info["webhook_url"] = webhook_url
        
        if not webhook_url:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid webhook path",
                    "debug": debug_info if debug_mode else None
                })
            }

        # Constructing the request body from the root of args
        body = {
            "content": args.get("content"),
            "embeds": args.get("embeds", [])
        }
        
        # Add color based on the importance level if AUTO_COLORS is enabled
        if not body.get('embeds'):
            body['embeds'] = [{}]
            
        # Update path variable to use last part for webhook type
        path = path.split('/')[-1] if len(path.split('/')) > 1 else ''
        
        # Check if auto colors are enabled (defaults to True if not set)
        auto_colors = os.environ.get('AUTO_COLORS', 'true').lower() == 'true'
        if auto_colors:
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
