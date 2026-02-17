from flask import Flask, jsonify, request
import requests
import re
from urllib.parse import unquote

app = Flask(__name__)

class EmailnatorAPI:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.emailnator.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; LAVA Blaze)',
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }

    def refresh_tokens(self):
        try:
            self.session.get(self.base_url, headers=self.headers, timeout=10)
            token = self.session.cookies.get('XSRF-TOKEN')
            if token:
                self.headers['X-XSRF-TOKEN'] = unquote(token)
                return True
            return False
        except:
            return False

    def clean_html(self, raw_html):
        clean_text = re.sub(r'<.*?>', ' ', raw_html)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text

bot = EmailnatorAPI()

@app.route('/')
def home():
    return "Emailnator API is Running on Vercel!"

@app.route('/generate', methods=['GET'])
def generate():
    if bot.refresh_tokens():
        url = f"{bot.base_url}/generate-email"
        payload = {"email": ["plusGmail", "dotGmail"]}
        resp = bot.session.post(url, json=payload, headers=bot.headers)
        if resp.status_code == 200:
            email = resp.json()['email'][0]
            return jsonify({"status": "success", "email": email})
    return jsonify({"status": "error", "message": "Token refresh failed"}), 419

@app.route('/inbox', methods=['GET'])
def get_inbox():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email parameter missing"}), 400
    
    bot.refresh_tokens() # Fresh session for inbox
    url_list = f"{bot.base_url}/message-list"
    resp = bot.session.post(url_list, json={"email": email}, headers=bot.headers)
    
    if resp.status_code == 200:
        messages = resp.json().get('messageData', [])
        valid_msgs = [m for m in messages if m['from'] != "AI TOOLS"]
        
        results = []
        for m in valid_msgs:
            m_id = m['messageID']
            body_resp = bot.session.post(url_list, json={"email": email, "messageID": m_id}, headers=bot.headers)
            clean_body = bot.clean_html(body_resp.text) if body_resp.status_code == 200 else "Body fetch error"
            
            # OTP detection (6 to 8 digits)
            otp_match = re.search(r'(\d{6,8})', clean_body)
            results.append({
                "from": m['from'],
                "subject": m['subject'],
                "body": clean_body,
                "otp": otp_match.group(1) if otp_match else None
            })
        return jsonify({"status": "success", "inbox": results})
    return jsonify({"status": "error", "code": resp.status_code})

# Vercel handle karega isko, app.run ki zaroorat nahi hai
