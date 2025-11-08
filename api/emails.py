from flask import jsonify, request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import logging
from utils.gmail_helper import analyze_email_priority, get_email_data
from utils.ai_helper import get_ai_labels, summarize_email

logger = logging.getLogger(__name__)

@api_bp.route('/api/analyze-all-emails', methods=['POST'])
def analyze_all_emails():
    """Analyze all emails with AI features"""
    try:
        data = request.json
        tokens = data.get('tokens')
        
        if not tokens:
            return jsonify({'success': False, 'error': 'No tokens provided'})
        
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
        
        yesterday = datetime.now() - timedelta(hours=24)
        query = f'after:{int(yesterday.timestamp())} in:inbox'
        
        result = service.users().messages().list(userId='me', maxResults=15, q=query).execute()
        messages = result.get('messages', [])
        
        emails = []
        priority_stats = {
            'work': 0,
            'medium': 0,
            'low': 0,
            'promotions': 0,
            'spam': 0,
            'total': len(messages)
        }
        
        for msg in messages:
            try:
                message = service.users().messages().get(
                    userId='me', 
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                headers = message.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
                
                try:
                    from email.utils import parsedate_to_datetime
                    date_obj = parsedate_to_datetime(date)
                    simple_date = date_obj.strftime("%b %d, %I:%M %p")
                except:
                    simple_date = date[:16] if len(date) > 16 else date
                
                sender_name = sender.split('<')[0].strip().replace('"', '') if '<' in sender else sender
                
                priority = analyze_email_priority(subject, message.get('snippet', ''), sender_name)
                priority_stats[priority] += 1
                
                # AI Analysis
                ai_labels = get_ai_labels(subject, message.get('snippet', ''), sender_name)
                summary = summarize_email(subject, message.get('snippet', ''), message.get('snippet', ''))
                
                emails.append({
                    'id': msg['id'],
                    'subject': subject,
                    'sender': sender_name,
                    'snippet': message.get('snippet', 'No preview available'),
                    'date': simple_date,
                    'priority': priority,
                    'ai_labels': ai_labels,
                    'summary': summary
                })
            except Exception as e:
                logger.warning(f"Error processing message {msg.get('id')}: {str(e)}")
                continue
        
        # Generate overall analysis
        overall_analysis = generate_overall_analysis(emails, priority_stats)
        
        return jsonify({
            'success': True, 
            'emails': emails,
            'stats': priority_stats,
            'analysis': overall_analysis
        })
        
    except Exception as e:
        logger.error(f"Analyze all emails error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/api/analyze-labels', methods=['POST'])
def analyze_labels():
    """Analyze email labels with AI"""
    try:
        data = request.json
        tokens = data.get('tokens')
        
        if not tokens:
            return jsonify({'success': False, 'error': 'No tokens provided'})
        
        credentials = Credentials(
            token=tokens['token'],
            refresh_token=tokens['refresh_token'],
            token_uri=tokens['token_uri'],
            client_id=tokens['client_id'],
            client_secret=tokens['client_secret'],
            scopes=tokens.get('scopes', [
                "https://www.googleapis.com/auth/gmail.readonly"
            ])
        )
        
        if credentials.expired:
            credentials.refresh(Request())
        
        service = build('gmail', 'v1', credentials=credentials)
        
        yesterday = datetime.now() - timedelta(hours=24)
        query = f'after:{int(yesterday.timestamp())} in:inbox'
        
        result = service.users().messages().list(userId='me', maxResults=10, q=query).execute()
        messages = result.get('messages', [])
        
        label_distribution = {}
        all_labels = []
        
        for msg in messages:
            try:
                message = service.users().messages().get(
                    userId='me', 
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From']
                ).execute()
                
                headers = message.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                sender_name = sender.split('<')[0].strip().replace('"', '') if '<' in sender else sender
                
                labels = get_ai_labels(subject, message.get('snippet', ''), sender_name)
                all_labels.extend(labels)
                
            except Exception as e:
                continue
        
        # Count label distribution
        for label in all_labels:
            label_distribution[label] = label_distribution.get(label, 0) + 1
        
        analysis = {
            'label_distribution': label_distribution,
            'recommendations': generate_label_recommendations(label_distribution)
        }
        
        return jsonify({
            'success': True, 
            'analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"Label analysis error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def generate_overall_analysis(emails, stats):
    """Generate overall analysis of emails"""
    try:
        from utils.ai_helper import setup_gemini
        
        model = setup_gemini()
        if not model:
            return "AI analysis completed. Review your emails for patterns."
        
        prompt = f"""
        Analyze this email dataset:
        - Total emails: {stats['total']}
        - Work priority: {stats['work']}
        - Medium priority: {stats['medium']} 
        - Low priority: {stats['low']}
        - Promotions: {stats['promotions']}
        
        Provide a brief 2-3 sentence analysis of the email patterns and one suggestion for productivity improvement.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except:
        return f"Analyzed {stats['total']} emails. {stats['work']} require immediate attention."

def generate_label_recommendations(label_distribution):
    """Generate recommendations based on label distribution"""
    try:
        from utils.ai_helper import setup_gemini
        
        model = setup_gemini()
        if not model:
            return "Consider creating filters for frequently occurring labels."
        
        prompt = f"""
        Based on this email label distribution: {label_distribution}
        Provide 2-3 practical recommendations for email management and organization.
        Keep it concise and actionable.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Consider creating filters for your most common email types to automate organization."
