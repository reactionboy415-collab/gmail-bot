from flask import Flask, jsonify, request
import requests
import re
from urllib.parse import unquote

app = Flask(__name__)

class EmailnatorAPI:
    def __init__(self):
        self.base_url = "https://www.emailnator.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
            'Origin': 'https://www.emailnator.com',
            'Referer': 'https://www.emailnator.com/'
        }

    def get_fresh_session(self):
        """Har request ke liye fresh session banayega"""
        session = requests.Session()
        try:
            # 1. Pehle tokens uthao
            r = session.get(self.base_url, headers=self.headers, timeout=10)
            token = session.cookies.get('XSRF-TOKEN')
            if token:
                # 2. Token ko headers mein update karo
                self.headers['X-XSRF-TOKEN'] = unquote(token)
                return session
            return None
        except Exception as e:
            return None

    def clean_html(self, raw_html):
        # Saare HTML tags hatane ke liye simple regex
        clean_text = re.sub(r'<.*?>', ' ', raw_html)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text

bot = EmailnatorAPI()

@app.route('/')
def home():
    return jsonify({"status": "active", "msg": "Bhai ki API Vercel par mast chal rahi hai!"})

@app.route('/generate', methods=['GET'])
def generate():
    session = bot.get_fresh_session()
    if not session:
        return jsonify({"error": "Failed to get session tokens"}), 419
    
    url = f"{bot.base_url}/generate-email"
    payload = {"email": ["plusGmail", "dotGmail"]}
    try:
        resp = session.post(url, json=payload, headers=bot.headers, timeout=10)
        if resp.status_code == 200:
            email = resp.json()['email'][0]
            return jsonify({"status": "success", "email": email})
        return jsonify({"error": "Server rejected request", "code": resp.status_code}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/inbox', methods=['GET'])
def get_inbox():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email parameter missing"}), 400
    
    session = bot.get_fresh_session()
    if not session:
        return jsonify({"error": "Failed to refresh tokens for inbox"}), 419
        
    url_list = f"{bot.base_url}/message-list"
    try:
        # 1. Message list fetch karo
        resp = session.post(url_list, json={"email": email}, headers=bot.headers, timeout=10)
        
        if resp.status_code == 200:
            messages = resp.json().get('messageData', [])
            valid_msgs = [m for m in messages if m['from'] != "AI TOOLS"]
            
            results = []
            for m in valid_msgs:
                m_id = m['messageID']
                # 2. Message body fetch karo
                body_resp = session.post(url_list, json={"email": email, "messageID": m_id}, headers=bot.headers, timeout=10)
                
                clean_body = "Body empty"
                otp = None
                
                if body_resp.status_code == 200:
                    clean_body = bot.clean_html(body_resp.text)
                    # 6-8 digit OTP dhoondo
                    otp_match = re.search(r'(\d{6,8})', clean_body)
                    otp = otp_match.group(1) if otp_match else None
                
                results.append({
                    "from": m['from'],
                    "subject": m['subject'],
                    "body": clean_body,
                    "otp": otp
                })
            
            return jsonify({"status": "success", "inbox": results, "count": len(results)})
        else:
            return jsonify({"error": "Could not fetch message list", "code": resp.status_code}), resp.status_code
            
    except Exception as e:
        # Crash hone ke bajaye error message return karega
        return jsonify({"error": "Internal Processing Error", "details": str(e)}), 500
