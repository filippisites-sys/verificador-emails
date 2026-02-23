"""
Backend Verificador de E-mails — Proxy
=======================================
Serve como intermediário entre o site (Hostinger)
e a API pública do rapid-email-verifier,
resolvendo o problema de CORS.
"""

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_URL = "https://rapid-email-verifier.fly.dev/api/validate"

STATUS_MAP = {
    "VALID":          ("valid",   "Válido"),
    "INVALID_FORMAT": ("invalid", "Formato inválido"),
    "INVALID_DOMAIN": ("invalid", "Domínio inexistente"),
    "INVALID_MX":     ("invalid", "Sem servidor de e-mail"),
    "DISPOSABLE":     ("invalid", "E-mail temporário"),
    "PROBABLY_VALID": ("risky",   "E-mail genérico (admin, info...)"),
}

@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json()
    if not data or "email" not in data:
        return jsonify({"status": "invalid", "reason": "E-mail não informado"}), 400

    email = data["email"].strip().lower()

    try:
        res = requests.get(API_URL, params={"email": email}, timeout=10)
        result = res.json()
        api_status = result.get("status", "UNKNOWN")
        status, reason = STATUS_MAP.get(api_status, ("risky", api_status))
        return jsonify({"status": status, "reason": reason})
    except Exception as e:
        return jsonify({"status": "risky", "reason": "Erro ao verificar"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
