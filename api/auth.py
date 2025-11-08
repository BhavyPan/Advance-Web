from flask import jsonify, request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

@api_bp.route('/api/auth/user', methods=['POST'])
def get_user_info():
    """Get user information from stored tokens"""
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
            scopes=tokens.get('scopes', [])
        )
        
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        return jsonify({
            'success': True,
            'user': user_info
        })
        
    except Exception as e:
        logger.error(f"User info error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
