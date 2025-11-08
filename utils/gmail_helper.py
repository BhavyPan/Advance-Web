import base64
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

def send_email(credentials, to, subject, body, cc=None, bcc=None):
    """Send an email using Gmail API"""
    try:
        service = build('gmail', 'v1', credentials=credentials)
        
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
            
        html_part = MIMEText(body, 'html')
        message.attach(html_part)
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        logger.info(f"Email sent successfully. Message ID: {sent_message['id']}")
        return {'success': True, 'message_id': sent_message['id']}
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_email_data(email_id, tokens):
    """Helper function to get email data"""
    try:
        credentials = Credentials(
            token=tokens['token'],
            refresh_token=tokens['refresh_token'],
            token_uri=tokens['token_uri'],
            client_id=tokens['client_id'],
            client_secret=tokens['client_secret'],
            scopes=tokens.get('scopes', [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify"
            ])
        )
        
        if credentials.expired:
            credentials.refresh(Request())
        
        service = build('gmail', 'v1', credentials=credentials)
        message = service.users().messages().get(userId='me', id=email_id, format='full').execute()
        
        headers = message.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        
        try:
            date_obj = parsedate_to_datetime(date)
            formatted_date = date_obj.strftime("%A, %B %d, %Y at %I:%M %p")
        except:
            formatted_date = date
        
        body = extract_email_body(message.get('payload', {}))
        priority = analyze_email_priority(subject, body, sender)
        
        return {
            'id': email_id,
            'subject': subject,
            'sender': sender.split('<')[0].strip().replace('"', '') if '<' in sender else sender,
            'date': formatted_date,
            'body': body,
            'priority': priority,
            'snippet': message.get('snippet', '')
        }
    except Exception as e:
        logger.error(f"Get email data error: {str(e)}")
        return None

def extract_email_body(payload):
    """Extract the email body from the payload"""
    try:
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/html' and 'body' in part and 'data' in part['body']:
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
                elif mime_type == 'text/plain' and 'body' in part and 'data' in part['body']:
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        if not body and 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        if not body:
            return "No email content available"
        
        return body
        
    except Exception as e:
        logger.error(f"Error extracting email body: {str(e)}")
        return "Error loading email content"

def analyze_email_priority(subject, snippet, sender):
    """AI-powered email priority analysis"""
    content = (subject + ' ' + snippet).lower()
    sender_lower = sender.lower()
    
    work_keywords = ['urgent', 'asap', 'important', 'project', 'meeting', 'deadline', 'boss', 'manager', 'team', 'report', 'presentation', 'review', 'action required']
    promo_keywords = ['sale', 'discount', 'offer', 'deal', 'promo', 'buy now', 'limited time', 'coupon', 'save', 'special', 'exclusive', 'offer']
    spam_keywords = ['winner', 'prize', 'free', 'congratulations', 'lottery', 'click here', 'unsubscribe', 'selected', 'cash', 'million']
    
    work_score = sum(1 for keyword in work_keywords if keyword in content)
    promo_score = sum(1 for keyword in promo_keywords if keyword in content)
    spam_score = sum(1 for keyword in spam_keywords if keyword in content)
    
    if any(domain in sender_lower for domain in ['company.com', 'work.com', 'corporate.com', 'hr.', 'manager']):
        work_score += 2
    
    if spam_score >= 2:
        return 'spam'
    elif work_score >= 2:
        return 'work'
    elif promo_score >= 2:
        return 'promotions'
    elif work_score >= 1:
        return 'medium'
    else:
        return 'low'
