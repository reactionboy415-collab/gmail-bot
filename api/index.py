from flask import Flask, jsonify, request
import requests
import re
from urllib.parse import unquote

app = Flask(__name__)

class EmailnatorAPI:
    def __init__(self):
        self.base_url = "https://www.emailnator.com"
        # Thode aur real headers taaki Vercel block na ho
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
            'Origin': 'https://www.emailnator.com',
            'Referer': 'https://www.emailnator.com/'
        }

    def get_session(self):
        """Vercel ke liye fresh session management"""
        session = requests.Session()
        try:
            # Pehle home page hit karo cookies ke liye
            session.get(self.base_url, headers=self.headers, timeout=10)
            token = session.cookies.get('XSRF-TOKEN')
            if token:
                # Token decode karke headers mein set karo
                self.headers['X-XSRF-TOKEN'] = unquote(token)
                return session
            return None
        except:
            return None

    def clean_html(self, raw_html):
        clean_text = re.sub(r'<.*?>', ' ', raw_html)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text

bot = EmailnatorAPI()

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "Emailnator API by Bhai 🚀"})

@app.route('/generate', methods=['GET'])
def generate():
    session = bot.get_session()
    if session:
        url = f"{bot.base_url}/generate-email"
        payload = {"email": ["plusGmail", "dotGmail"]}
        resp = session.post(url, json=payload, headers=bot.headers)
        if resp.status_code == 200:
            email = resp.json()['email'][0]
            return jsonify({"status": "success", "email": email})
        return jsonify({"status": "error", "code": resp.status_code, "msg": "Generation failed"}), resp.status_code
    return jsonify({"status": "error", "message": "Token fetch failed"}), 419

@app.route('/inbox', methods=['GET'])
def get_inbox():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email parameter missing"}), 400
    
    session = bot.get_session()
    if not session:
        return jsonify({"error": "Failed to establish session"}), 419
        
    url_list = f"{bot.base_url}/message-list"
    resp = session.post(url_list, json={"email": email}, headers=bot.headers)
    
    if resp.status_code == 200:
        messages = resp.json().get('messageData', [])
        valid_msgs = [m for m in messages if m['from'] != "AI TOOLS"]
        
        results = []
        for m in valid_msgs:
            m_id = m['messageID']
            body_resp = session.post(url_list, json={"email": email, "messageID": m_id}, headers=bot.headers)
            clean_body = bot.clean_html(body_resp.text) if body_resp.status_code == 200 else "Body fetch error"
            
            otp_match = re.search(r'(\d{6,8})', clean_body)
            results.append({
                "from": m['from'],
                "subject": m['subject'],
                "body": clean_body,
                "otp": otp_match.group(1) if otp_match else None
            })
        return jsonify({"status": "success", "inbox": results, "count": len(results)})
    return jsonify({"status": "error", "code": resp.status_code})

# For Vercel, app object is the entry point
