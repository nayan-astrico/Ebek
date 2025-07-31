import boto3
import logging
import os
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)

# Get AWS credentials from environment variables
# No need to call load_dotenv() again since it's already loaded in settings.py
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')

# Initialize SES client
try:
    ses = boto3.client(
        "ses",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
except Exception as e:
    logger.error(f"Failed to initialize SES client: {e}")
    ses = None

def send_email(subject, body, to_addresses):
    if not ses:
        logger.error("SES client not initialized. Check AWS credentials.")
        return None
        
    try:
        response = ses.send_email(
            Source="nayan@astrico.ai",
            Destination={"ToAddresses": to_addresses},
            Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}}
        )
        logger.info(f"Email sent: {response['MessageId']}")
        return response['MessageId']
    except ClientError as e:
        logger.error(f"AWS Error sending email: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return None

