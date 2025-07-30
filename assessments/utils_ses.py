import boto3
import logging
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables with error handling
try:
    load_dotenv()
    logger.info("Successfully loaded environment variables from .env file")
except Exception as e:
    logger.error(f"Failed to load environment variables: {e}")
    raise

# Get AWS credentials from environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'AKIAQGYBPNQU7R2CPYH6')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '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')
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

