from flask import jsonify, request
import logging
from utils.ai_helper import setup_gemini

logger = logging.getLogger(__name__)

@api_bp.route('/api/ai-enhance-email', methods=['POST'])
def ai_enhance_email():
    """Enhance email content with AI"""
    try:
        data = request.json
        subject = data.get('subject', '')
        body = data.get('body', '')
        
        if not body:
            return jsonify({'success': False, 'error': 'Email body is required'})
        
        model = setup_gemini()
        if not model:
            return jsonify({'success': False, 'error': 'AI service unavailable'})
        
        prompt = f"""
        Please enhance and improve this email content. Make it more professional, clear, and effective:
        
        Subject: {subject}
        Current Content: {body}
        
        Please return only the enhanced version of the email body content, maintaining the original intent but improving clarity, grammar, and professionalism.
        """
        
        response = model.generate_content(prompt)
        enhanced_body = response.text
        
        return jsonify({
            'success': True, 
            'enhanced_body': enhanced_body
        })
        
    except Exception as e:
        logger.error(f"AI enhance error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/api/speech-to-text', methods=['POST'])
def speech_to_text():
    """Speech to text endpoint - placeholder for deployment"""
    return jsonify({
        'success': True, 
        'text': 'Voice input is not available in the deployed version. Please use text input instead. This is a demonstration of the voice interface.'
    })
