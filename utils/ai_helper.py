import logging
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

def setup_gemini():
    """Setup Gemini AI"""
    try:
        api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyBc4XCu2aOs6eKJqu1AXJ2Vwa5qK1bamB8")
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        logger.error(f"Gemini setup error: {str(e)}")
        return None

def summarize_email(subject, body, snippet):
    """Generate AI summary for email"""
    try:
        model = setup_gemini()
        if not model:
            return "AI summarization unavailable"
        
        prompt = f"""
        Please provide a concise summary of this email in 2-3 bullet points:
        
        Subject: {subject}
        Content: {body if body else snippet}
        
        Focus on:
        - Main purpose of the email
        - Key action items required
        - Important details or deadlines
        
        Format as bullet points.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Summarization error: {str(e)}")
        return "Unable to generate summary"

def generate_smart_reply(subject, body, sender):
    """Generate smart AI reply"""
    try:
        model = setup_gemini()
        if not model:
            return "AI reply generation unavailable"
        
        prompt = f"""
        Generate a professional email reply for this message:
        
        From: {sender}
        Subject: {subject}
        Content: {body}
        
        Provide 3 different reply options:
        1. Professional and formal
        2. Casual and friendly  
        3. Quick acknowledgment
        
        Format each option clearly.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Smart reply error: {str(e)}")
        return "Unable to generate smart replies"

def generate_ai_composed_email(context, recipient, purpose, tone="professional"):
    """Generate AI-composed email from scratch"""
    try:
        model = setup_gemini()
        if not model:
            return "AI composition unavailable"
        
        prompt = f"""
        Compose an email with the following details:
        
        Recipient: {recipient}
        Purpose: {purpose}
        Context: {context}
        Tone: {tone}
        
        Please generate a complete email with:
        - Appropriate subject line
        - Professional greeting
        - Clear and concise body content
        - Professional closing
        
        Make sure the email is well-structured and appropriate for the given context and tone.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"AI composition error: {str(e)}")
        return "Unable to generate email content"

def get_ai_labels(subject, content, sender):
    """Get AI-generated labels for email"""
    try:
        model = setup_gemini()
        if not model:
            return ["general"]
        
        prompt = f"""
        Analyze this email and assign relevant labels from these categories:
        - work
        - personal  
        - urgent
        - follow-up
        - meeting
        - project
        - finance
        - travel
        - social
        - newsletter
        - promotion
        - notification
        
        Email:
        Subject: {subject}
        From: {sender}
        Content: {content[:1000]}
        
        Return only the most relevant 2-3 labels as a comma-separated list.
        """
        
        response = model.generate_content(prompt)
        labels = [label.strip().lower() for label in response.text.split(',')]
        return labels[:3]
    except Exception as e:
        logger.error(f"AI labeling error: {str(e)}")
        return ["general"]
