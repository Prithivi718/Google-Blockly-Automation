import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from re import sub
from google_apis import create_service
from bs4 import BeautifulSoup



def init_gmail_service():
    client_secret_file = "client_secret.json"
    API_SERVICE_NAME= 'gmail'
    API_VERSION= 'v1'
    SCOPES= ['https://mail.google.com/']

    service = create_service(client_secret_file, API_SERVICE_NAME, API_VERSION, SCOPES)

    return service



def list_email_msg(service, filter_query):

    try:
        result = service.users().messages().list(maxResults= 5,userId='me', q= filter_query).execute()
        return result
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return


def get_msg_details(service, messages):
    # messages is a list of dictionaries where each dictionary contains a message id.

    # iterate through all the messages
    for msg in messages:
        # Get the message from its id
        try:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        except Exception as e:
            print(f"Error fetching message {msg.get('id', 'unknown')}: {e}")
            continue

        # Use try-except to avoid any Errors
        try:
            # Get value of 'payload' from dictionary 'txt'
            payload = txt['payload']
            headers = payload['headers']

            # Initialize variables
            subject = "No Subject"
            sender = "Unknown Sender"

            # Look for Subject and Sender Email in the headers
            for d in headers:
                if d['name'] == 'Subject':
                    subject = d['value']
                if d['name'] == 'From':
                    sender = d['value']

            # The Body of the message is in Encrypted format. So, we have to decode it.
            # Get the data and decode it with base 64 decoder.
            body = "No body content"
            
            # Check if email has parts (multipart) or direct body (simple text)
            if 'parts' in payload and payload['parts']:
                parts = payload['parts'][0]
                if 'body' in parts and 'data' in parts['body']:
                    data = parts['body']['data']
                    data = data.replace("-","+").replace("_","/")
                    decoded_data = base64.b64decode(data)
                    # Now, the data obtained is in lxml. So, we will parse 
                    # it with BeautifulSoup library
                    soup = BeautifulSoup(decoded_data , "lxml")
                    body = soup.get_text() if soup.body is None else soup.body.get_text()
            elif 'body' in payload and 'data' in payload['body']:
                # Simple text email without parts
                data = payload['body']['data']
                data = data.replace("-","+").replace("_","/")
                decoded_data = base64.b64decode(data)
                body = decoded_data.decode('utf-8')

            # Printing the subject, sender's email and message
            print("Subject: ", subject)
            print("From: ", sender)
            print("Message: ", body)
            print('\n')

        except Exception as e:
            print(f"Error processing message {msg.get('id', 'unknown')}: {e}")
            continue

    return (subject, sender, body)


def mark_as_read(service, message_id):
    """
    Mark an email as read by removing the UNREAD label.
    
    Args:
        service: Gmail API service object
        message_id: String ID of the message to mark as read
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        print(f"Email {message_id} marked as read")
        return True
    except Exception as e:
        print(f"Error marking email {message_id} as read: {e}")
        return False


def mark_multiple_as_read(service, message_ids):
    """
    Mark multiple emails as read by removing the UNREAD label.
    
    Args:
        service: Gmail API service object
        message_ids: List of message ID strings to mark as read
    
    Returns:
        int: Number of successfully marked emails
    """
    success_count = 0
    for msg_id in message_ids:
        if mark_as_read(service, msg_id):
            success_count += 1
    return success_count




