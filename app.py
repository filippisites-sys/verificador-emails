"""
Backend de Verificação de E-mails
==================================
Instalar dependências:
  pip install flask flask-cors dnspython

Rodar localmente:
  python app.py

Rodar em produção (Render/Railway):
  Eles detectam automaticamente — só suba a pasta.
"""

import re
import smtplib
import socket
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

app = Flask(__name__)
CORS(app)  # Permite chamadas do seu site na Hostinger

# ── VALIDAÇÃO DE SINTAXE ──
def check_syntax(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ── MX LOOKUP ──
def get_mx_record(domain: str):
    if not DNS_AVAILABLE:
        return None
    try:
        records = dns.resolver.resolve(domain, 'MX', lifetime=5)
        mx_list = sorted(records, key=lambda r: r.preference)
        return str(mx_list[0].exchange).rstrip('.')
    except Exception:
        return None

# ── VERIFICAÇÃO SMTP ──
def verify_smtp(email: str, mx_host: str) -> dict:
    sender = "verify@verification.com"
    try:
        with smtplib.SMTP(timeout=8) as smtp:
            smtp.connect(mx_host, 25)
            smtp.ehlo('verification.com')
            smtp.mail(sender)
            code, message = smtp.rcpt(email)
            smtp.quit()

            if code == 250:
                # Testa catch-all: tenta um email claramente inexistente
                domain = email.split('@')[1]
                fake = f"naoexiste_xyz_12345@{domain}"
                try:
                    with smtplib.SMTP(timeout=5) as smtp2:
                        smtp2.connect(mx_host, 25)
                        smtp2.ehlo('verification.com')
                        smtp2.mail(sender)
                        code2, _ = smtp2.rcpt(fake)
                        smtp2.quit()
                    if code2 == 250:
                        return {"status": "risky", "reason": "Catch-all detectado"}
                except Exception:
                    pass
                return {"status": "valid", "reason": "Verificado"}

            elif code in (550, 551, 552, 553, 554):
                return {"status": "invalid", "reason": f"Caixa não existe ({code})"}
            elif code in (421, 450, 451, 452):
                return {"status": "risky", "reason": "Servidor temporariamente indisponível"}
            else:
                return {"status": "risky", "reason": f"Resposta desconhecida ({code})"}

    except smtplib.SMTPConnectError:
        return {"status": "risky", "reason": "Porta 25 bloqueada"}
    except smtplib.SMTPException as e:
        return {"status": "risky", "reason": "Erro SMTP"}
    except socket.timeout:
        return {"status": "risky", "reason": "Timeout de conexão"}
    except Exception:
        return {"status": "risky", "reason": "Erro de conexão"}

# ── ROTA PRINCIPAL ──
@app.route('/verify', methods=['POST'])
def verify_email():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"status": "invalid", "reason": "E-mail não informado"}), 400

    email = data['email'].strip().lower()

    # 1. Sintaxe
    if not check_syntax(email):
        return jsonify({"status": "invalid", "reason": "Sintaxe inválida"})

    # 2. MX lookup
    domain = email.split('@')[1]
    mx = get_mx_record(domain)
    if not mx:
        return jsonify({"status": "invalid", "reason": "Domínio sem servidor de e-mail"})

    # 3. SMTP
    result = verify_smtp(email, mx)
    return jsonify(result)

# ── ROTA DE SAÚDE ──
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Backend de verificação rodando!"})

# ── INICIAR ──
if __name__ == '__main__':
    print("🚀 Backend iniciado em http://localhost:5000")
    print("📍 Endpoint: POST /verify")
    print("   Body: { \"email\": \"exemplo@dominio.com\" }")
    app.run(host='0.0.0.0', port=5000, debug=False)
