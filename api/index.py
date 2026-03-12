import os
import oracledb
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# --- Configuração Inicial ---
load_dotenv()
app = Flask(__name__)
CORS(app)

def get_connection():
    """Tenta conectar ao Oracle usando variáveis de ambiente da Vercel"""
    user = os.environ.get("DB_USER")
    pw = os.environ.get("DB_PASSWORD")
    dsn = os.environ.get("DB_DSN")
    
    if not user or not pw:
        return None
        
    try:
        # Modo Thin do oracledb com timeout curto para evitar travamento na Vercel
        return oracledb.connect(
            user=user, 
            password=pw, 
            dsn=dsn, 
            expire_time=1
        )
    except Exception as e:
        print(f"Falha na conexão real com o Oracle: {e}")
        return None

# --------------------------------
# ROTA PRINCIPAL (Front-end Embutido)
# --------------------------------
@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>Hero Manager Pro</title>
        <style>
            :root { --bg: #121212; --card: #1e1e1e; --primary: #bb86fc; --sec: #03dac6; --danger: #cf6679; --text: #e1e1e1; }
            body { background: var(--bg); color: var(--text); font-family: sans-serif; display: flex; flex-direction: column; align-items: center; margin: 0; }
            header { width: 100%; padding: 20px; text-align: center; background: #1f1f1f; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
            .container { width: 90%; max-width: 800px; margin-top: 30px; }
            button { background: var(--sec); color: #000; border: none; padding: 15px 30px; font-weight: bold; border-radius: 5px; cursor: pointer; width: 100%; margin-bottom: 30px; }
            #lista-herois { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
            .card { background: var(--card); padding: 20px; border-radius: 10px; border-left: 5px solid var(--primary); }
            .card.caido { border-left-color: var(--danger); opacity: 0.6; filter: grayscale(1); }
            .hp-bg { background: #333; height: 10px; border-radius: 5px; margin: 10px 0; overflow: hidden; }
            .hp-bar { background: linear-gradient(90deg, #ff4b2b, #ff416c); height: 100%; transition: width 0.5s; }
            .msg-erro { color: var(--danger); text-align: center; grid-column: 1 / -1; }
        </style>
    </head>
    <body onload="carregar()">
        <header><h1>⚔️ SISTEMA DE BATALHA</h1></header>
        <div class="container">
            <button onclick="processarTurno()" id="btn-turno">AVANÇAR TURNO (DANO DE NÉVOA)</button>
            <div id="lista-herois">Buscando dados no banco...</div>
        </div>
        <script>
            async function carregar() {
                try {
                    const res = await fetch('/herois');
                    const dados = await res.json();
                    
                    const container = document.getElementById('lista-herois');
                    
                    if (dados.erro) {
                        container.innerHTML = `<p class="msg-erro">❌ ${dados.erro}</p>`;
                        return;
                    }

                    container.innerHTML = dados.map(h => `
                        <div class="card ${h.status === 'CAIDO' ? 'caido' : ''}">
                            <strong>${h.nome}</strong> (${h.classe})<br>
                            <div class="hp-bg"><div class="hp-bar" style="width: ${(h.hp_atual/h.hp_max)*100}%"></div></div>
                            <small>HP: ${h.hp_atual}/${h.hp_max} - ${h.status}</small>
                        </div>
                    `).join('');
                } catch (e) {
                    document.getElementById('lista-herois').innerHTML = '<p class="msg-erro">❌ Erro ao conectar na API</p>';
                }
            }

            async function processarTurno() {
                const btn = document.getElementById('btn-turno');
                btn.innerText = "PROCESSANDO..."; btn.disabled = true;
                await fetch('/proximo-turno', { method: 'POST' });
                await carregar();
                btn.innerText = "AVANÇAR TURNO (DANO DE NÉVOA)"; btn.disabled = false;
            }
        </script>
    </body></html>
    """

# --------------------------------
# API: LISTAR HERÓIS
# --------------------------------
@app.route("/herois", methods=["GET"])
def api_listar_herois():
    conn = get_connection()
    if not conn:
        return jsonify({"erro": "O banco de dados não permitiu a conexão (Firewall/IP)."}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_heroi, nome, classe, hp_atual, hp_max, status FROM TB_HEROIS")
        dados = cursor.fetchall()
        herois = [{"id": h[0], "nome": h[1], "classe": h[2], "hp_atual": h[3], "hp_max": h[4], "status": h[5]} for h in dados]
        return jsonify(herois), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        conn.close()

# --------------------------------
# API: PRÓXIMO TURNO
# --------------------------------
@app.route("/proximo-turno", methods=["POST"])
def api_proximo_turno():
    conn = get_connection()
    if not conn:
        return jsonify({"erro": "Falha na conexão com o banco"}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE TB_HEROIS SET hp_atual = hp_atual - 15 WHERE status = 'ATIVO'")
        cursor.execute("UPDATE TB_HEROIS SET status = 'CAIDO' WHERE hp_atual <= 0")
        conn.commit()
        return jsonify({"sucesso": True}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run()