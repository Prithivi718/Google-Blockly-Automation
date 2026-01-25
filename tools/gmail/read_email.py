from .gmail_api import init_gmail_service, list_email_msg, get_msg_details, mark_multiple_as_read

def query():
    return "from:'valtryek76' subject:'You have been assigned 5 problem sets' is:unread newer_than:1h"



def read_emails():
    # Initialize service inside the function to handle errors better
    try:
        service = init_gmail_service()
        if service is None:
            print("Failed to initialize Gmail service")
            return
    except Exception as e:
        print(f"Error initializing Gmail service: {e}")
        return

    filter_query = query()

    result = list_email_msg(service, filter_query)

    # We can also pass maxResults to get any number of emails. Like this:
    # result = service.users().messages().list(maxResults=200, userId='me').execute()
    messages = result.get('messages', [])

    if not messages:
        print("No messages found.")
        return
    
    subject, sender, body = get_msg_details(service, messages)

    msg_ids = [msg['id'] for msg in messages]

    mark_multiple_as_read(service, msg_ids)

    return (subject, sender, body)

    