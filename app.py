import os
import sys
from pathlib import Path

# Vercel-specific setup
if os.environ.get('VERCEL'):
    sys.path.append(str(Path(__file__).parent))
    os.environ['FLASK_ENV'] = 'production'

from flask import Flask, request, redirect, url_for, flash, render_template, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import json
import base64
from datetime import datetime, timedelta
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBc4XCu2aOs6eKJqu1AXJ2Vwa5qK1bamB8")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-123")

app.secret_key = SECRET_KEY

# OAuth Scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

# Import utilities
from utils.ai_helper import setup_gemini, summarize_email, generate_smart_reply, generate_ai_composed_email, get_ai_labels
from utils.gmail_helper import send_email, get_email_data, extract_email_body, analyze_email_priority

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/auth')
def auth():
    """Start the OAuth flow"""
    try:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            flash("OAuth configuration missing. Please check environment variables.")
            return redirect('/')
            
        domain = request.host_url.rstrip('/')
        redirect_uri = f"{domain}/oauth_callback"
        
        logger.info(f"Starting OAuth flow with redirect_uri: {redirect_uri}")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
        
        logger.info(f"Generated auth URL with {len(SCOPES)} scopes")
        return redirect(authorization_url)
        
    except Exception as e:
        error_msg = f'OAuth setup failed: {str(e)}'
        logger.error(f"OAuth Error: {error_msg}")
        flash(error_msg)
        return redirect('/')

@app.route('/oauth_callback')
def oauth_callback():
    """OAuth callback handler"""
    try:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            flash("OAuth configuration missing.")
            return redirect('/')
            
        domain = request.host_url.rstrip('/')
        redirect_uri = f"{domain}/oauth_callback"
        
        logger.info(f"Handling OAuth callback with redirect_uri: {redirect_uri}")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            state=request.args.get('state')
        )
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        logger.info(f"Token fetched successfully! Granted {len(credentials.scopes)} scopes")
        
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        credentials_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        return render_template('home.html', 
                             auth_success=True,
                             user_info=user_info,
                             credentials=json.dumps(credentials_data))
        
    except Exception as e:
        error_msg = f'Sign in failed: {str(e)}'
        logger.error(f"OAuth Callback Error: {error_msg}")
        flash(error_msg)
        return redirect('/')

@app.route('/inbox')
def inbox():
    return render_template('inbox.html')

@app.route('/compose')
def compose():
    return render_template('compose.html')

@app.route('/ai-compose')
def ai_compose():
    return render_template('ai-compose.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/smart-labels')
def smart_labels():
    return render_template('smart-labels.html')

@app.route('/compose-voice')
def compose_voice():
    return render_template('compose-voice.html')

@app.route('/email/<email_id>')
def view_email(email_id):
    return render_template('email-view.html', email_id=email_id)

@app.route('/email/<email_id>/summary')
def email_summary(email_id):
    return render_template('email-summary.html', email_id=email_id)

@app.route('/email/<email_id>/smart-reply')
def smart_reply(email_id):
    return render_template('smart-reply.html', email_id=email_id)

# API Routes
@app.route('/api/emails', methods=['POST'])
def api_emails():
    """API endpoint to fetch emails"""
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
            scopes=tokens.get('scopes', SCOPES)
        )
        
        if credentials.expired:
            try:
                credentials.refresh(Request())
                tokens['token'] = credentials.token
            except Exception as refresh_error:
                return jsonify({'success': False, 'error': f'Token refresh failed: {str(refresh_error)}'})
        
        service = build('gmail', 'v1', credentials=credentials)
        
        yesterday = datetime.now() - timedelta(hours=24)
        query = f'after:{int(yesterday.timestamp())} in:inbox'
        
        result = service.users().messages().list(
            userId='me', 
            maxResults=20,
            q=query
        ).execute()
        
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
        
        for msg in messages[:15]:
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
                
                ai_labels = get_ai_labels(subject, message.get('snippet', ''), sender_name)
                
                emails.append({
                    'id': msg['id'],
                    'subject': subject,
                    'sender': sender_name,
                    'snippet': message.get('snippet', 'No preview available'),
                    'date': simple_date,
                    'priority': priority,
                    'ai_labels': ai_labels
                })
            except Exception as e:
                logger.warning(f"Error processing message {msg.get('id')}: {str(e)}")
                continue
        
        return jsonify({
            'success': True, 
            'emails': emails,
            'stats': priority_stats
        })
        
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-email', methods=['POST'])
def api_send_email():
    """API endpoint to send email"""
    try:
        data = request.json
        tokens = data.get('tokens')
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        
        if not tokens or not to or not subject or not body:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        credentials = Credentials(
            token=tokens['token'],
            refresh_token=tokens['refresh_token'],
            token_uri=tokens['token_uri'],
            client_id=tokens['client_id'],
            client_secret=tokens['client_secret'],
            scopes=tokens.get('scopes', SCOPES)
        )
        
        html_body = f"<div style='font-family: Arial, sans-serif; line-height: 1.6;'>{body.replace(chr(10), '<br>')}</div>"
        
        result = send_email(credentials, to, subject, html_body, cc, bcc)
        
        if result['success']:
            return jsonify({'success': True, 'message_id': result['message_id']})
        else:
            return jsonify({'success': False, 'error': result['error']})
            
    except Exception as e:
        logger.error(f"Send email error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai-compose-email', methods=['POST'])
def api_ai_compose_email():
    """API endpoint for AI email composition"""
    try:
        data = request.json
        recipient = data.get('recipient')
        purpose = data.get('purpose')
        context = data.get('context', '')
        tone = data.get('tone', 'professional')
        
        if not recipient or not purpose:
            return jsonify({'success': False, 'error': 'Recipient and purpose are required'})
        
        email_content = generate_ai_composed_email(context, recipient, purpose, tone)
        
        return jsonify({
            'success': True, 
            'email_content': email_content
        })
        
    except Exception as e:
        logger.error(f"AI compose error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/<email_id>', methods=['POST'])
def api_get_email(email_id):
    """API endpoint to get a single email's full content"""
    try:
        data = request.json
        tokens = data.get('tokens')
        
        if not tokens:
            return jsonify({'success': False, 'error': 'No tokens provided'})
        
        email_data = get_email_data(email_id, tokens)
        
        if email_data:
            return jsonify({
                'success': True, 
                'email': email_data
            })
        else:
            return jsonify({'success': False, 'error': 'Could not fetch email'})
        
    except Exception as e:
        logger.error(f"API Email Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/<email_id>/analyze', methods=['POST'])
def api_analyze_email(email_id):
    """API endpoint for AI email analysis"""
    try:
        data = request.json
        tokens = data.get('tokens')
        
        if not tokens:
            return jsonify({'success': False, 'error': 'No tokens provided'})
        
        email_data = get_email_data(email_id, tokens)
        if not email_data:
            return jsonify({'success': False, 'error': 'Could not fetch email'})
        
        email_data['summary'] = summarize_email(
            email_data['subject'], 
            email_data.get('body', email_data['snippet']), 
            email_data['snippet']
        )
        
        email_data['ai_labels'] = get_ai_labels(
            email_data['subject'],
            email_data.get('body', email_data['snippet']),
            email_data['sender']
        )
        
        return jsonify({
            'success': True, 
            'email': email_data
        })
        
    except Exception as e:
        logger.error(f"Email analysis error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/email/<email_id>/smart-reply', methods=['POST'])
def api_smart_reply(email_id):
    """API endpoint for smart reply generation"""
    try:
        data = request.json
        tokens = data.get('tokens')
        
        if not tokens:
            return jsonify({'success': False, 'error': 'No tokens provided'})
        
        email_data = get_email_data(email_id, tokens)
        if not email_data:
            return jsonify({'success': False, 'error': 'Could not fetch email'})
        
        smart_replies = generate_smart_reply(
            email_data['subject'],
            email_data.get('body', email_data['snippet']),
            email_data['sender']
        )
        
        return jsonify({
            'success': True, 
            'replies': smart_replies
        })
        
    except Exception as e:
        logger.error(f"Smart reply error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
