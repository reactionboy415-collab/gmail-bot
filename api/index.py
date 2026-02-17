from flask import Flask, jsonify, request
import requests
import re
from urllib.parse import unquote

app = Flask(__name__)

class GmailnatorAPI:
    def __init__(self):
        self.base_url = "https://www.emailnator.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; LAVA Blaze) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }

    def clean_html(self, raw_html):
        # Script aur Style tags hatao
        clean_text = re.sub(r'<(script|style).*?>.*?</\1>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
        # Baki tags hatao
        clean_text = re.sub(r'<.*?>', ' ', clean_text)
        # Spaces clean karo
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        # Entities replace karo
        entities = {'&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"'}
        for k, v in entities.items():
            clean_text = clean_text.replace(k, v)
        return clean_text

    def get_session_and_token(self):
        session = requests.Session()
        try:
            session.get(self.base_url, headers=self.headers, timeout=10)
            token = session.cookies.get('XSRF-TOKEN')
            if token:
                # Flask headers dictionary update karega
                headers = self.headers.copy()
                headers['X-XSRF-TOKEN'] = unquote(token)
                return session, headers
            return None, None
        except:
            return None, None

bot_logic = GmailnatorAPI()

@app.route('/')
def home():
    return "🔥 Gmailnator API is Live & Working! 🔥"

@app.route('/generate', methods=['GET'])
def generate():
    session, headers = bot_logic.get_session_and_token()
    if not session:
        return jsonify({"error": "Failed to get tokens"}), 419
    
    url = f"{bot_logic.base_url}/generate-email"
    payload = {"email": ["plusGmail", "dotGmail"]}
    try:
        resp = session.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            return jsonify({"status": "success", "email": resp.json()['email'][0]})
        return jsonify({"error": "Failed to generate email"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/inbox', methods=['GET'])
def get_inbox():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email required"}), 400
    
    session, headers = bot_logic.get_session_and_token()
    if not session:
        return jsonify({"error": "Token refresh failed"}), 419
        
    url = f"{bot_logic.base_url}/message-list"
    try:
        # 1. Fetch Message List
        list_resp = session.post(url, json={"email": email}, headers=headers, timeout=10)
        if list_resp.status_code != 200:
            return jsonify({"error": "Inbox error", "code": list_resp.status_code}), list_resp.status_code
            
        messages = list_resp.json().get('messageData', [])
        valid_msgs = [m for m in messages if m['from'] != "AI TOOLS"]
        
        final_inbox = []
        for m in valid_msgs:
            m_id = m['messageID']
            # 2. Fetch Body (Yeh wahi logic hai jo list object error solve karega)
            body_resp = session.post(url, json={"email": email, "messageID": m_id}, headers=headers, timeout=10)
            
            raw_body = body_resp.text if body_resp.status_code == 200 else ""
            clean_body = bot_logic.clean_html(raw_body)
            
            # Message formatting (Pydroid ki tarah)
            main_text = clean_body.split("Time:")[-1].strip() if "Time:" in clean_body else clean_body
            
            otp_match = re.search(r'(\d{6})', clean_body)
            
            final_inbox.append({
                "from": m['from'],
                "subject": m['subject'],
                "body": main_text,
                "otp": otp_match.group(1) if otp_match else None
            })
            
        return jsonify({"status": "success", "inbox": final_inbox})
        
    except Exception as e:
        return jsonify({"error": "Internal Error", "details": str(e)}), 500
