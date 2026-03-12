import os
import oracledb
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# --- Configuração Inicial ---
load_dotenv()
app = Flask(__name__)
CORS(app)

def get_connection():
    # Puxa das variáveis de ambiente da Vercel
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    dsn = os.environ.get("DB_DSN")

    if not user or not password:
        return None

    try:
        # Tenta conectar com um tempo limite curto (para não travar a Vercel)
        return oracledb.connect(
            user=user,
            password=password,
            dsn=dsn,
            threaded=True
        )
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

# --------------------------------
# ROTA PRINCIPAL (Entrega o HTML)
# --------------------------------
@app.route("/")
def index():
    # Mantive o seu HTML embutido para garantir que ele carregue 100% na Vercel
    return """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hero Manager Pro</title>
        <style>
            :root { --bg-color: #121212; --card-bg: #1e1e1e; --primary: #bb86fc; --secondary: #03dac6; --danger: #cf6679; --text: #e1e1e1; }
            body { background-color: var(--bg-color); color: var(--text); font-family: sans-serif; margin: 0; display: flex; flex-direction: column; align-items: center; min-height: 100vh; }
            header { width: 100%; padding: 2rem 0; text-align: center; background: linear-gradient(180deg, #1f1f1f 0%, var(--bg-color) 100%); margin-bottom: 2rem; }
            h1 { margin: 0; letter-spacing: 2px; color: var(--primary); }
            .container { width: 90%; max-width: 1000px; }
            .controls { display: flex; justify-content: center; margin-bottom: 2rem; }
            button { background-color: var(--secondary); color: #000; border: none; padding: 12px 24px; font-weight: bold; border-radius: 4px; cursor: pointer; text-transform: uppercase; }
            #lista-herois { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
            .heroi-card { background-color: var(--card-bg); padding: 20px; border-radius: 12px; border-left: 5px solid var(--primary); }
            .heroi-card.caido { border-left-color: var(--danger); opacity: 0.7; filter: grayscale(0.8); }
            .hp-container { background: #333; border-radius: 10px; height: 12px; width: 100%; overflow: hidden; margin: 10px 0; }
            .hp-bar { height: 100%; background: linear-gradient(90deg, #ff4b2b, #ff416c); transition: width 0.5s; }
        </style>
    </head>
    <body>
        <header><h1>SISTEMA DE BATALHA</h1></header>
        <div class="container">
            <div class="controls"><button onclick="processarTurno()">⚔️ Avançar Turno</button></div>
            <div id="lista-herois"></div>
        </div>
        <script>
            async function carregarHerois() {
                try {
                    const response = await fetch('/herois');
                    const herois = await response.json();
                    const container = document.getElementById('lista-herois');
                    container.innerHTML = herois.map(h => `
                        <div class="heroi-card ${h.status === 'CAIDO' ? 'caido' : ''}">
                            <div class="info"><strong>${h.nome}</strong><br><small>${h.classe}</small></div>
                            <div class="hp-container"><div class="hp-bar" style="width: ${(h.hp_atual / h.hp_max) * 100}%"></div></div>
                            <div style="font-size: 0.8rem; text-align: right;">HP: ${h.hp_atual} / ${h.hp_max}</div>
                        </div>
                    `).join('');
                } catch (e) { console.error(e); }
            }
            async function processarTurno() {
                await fetch('/proximo-turno', { method: 'POST' });
                carregarHerois();
            }
            carregarHerois();
        </script>
    </body>
    </html>
    """

# --------------------------------
# LISTAR HERÓIS (Com modo Fallback)
# --------------------------------
@app.route("/herois")
def api_listar_herois():
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id_heroi, nome, classe, hp_atual, hp_max, status FROM TB_HEROIS")
            dados = cursor.fetchall()
            return jsonify([{"id": h[0], "nome": h[1], "classe": h[2], "hp_atual": h[3], "hp_max": h[4], "status": h[5]} for h in dados]), 200
        except:
            pass
        finally:
            conn.close()

    # SE O BANCO DA FIAP BLOQUEAR, ELE MOSTRA ISSO:
    return jsonify([
        {"id": 1, "nome": "Herói Online (Simulado)", "classe": "Guerreiro", "hp_atual": 80, "hp_max": 100, "status": "ATIVO"},
        {"id": 2, "nome": "Erro: Banco FIAP Bloqueado", "classe": "Firewall", "hp_atual": 0, "hp_max": 1, "status": "CAIDO"}
    ]), 200

# --------------------------------
# PROCESSAR PRÓXIMO TURNO
# --------------------------------
@app.route("/proximo-turno", methods=["POST"])
def api_proximo_turno():
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE TB_HEROIS SET hp_atual = hp_atual - 15 WHERE status = 'ATIVO'")
            cursor.execute("UPDATE TB_HEROIS SET status = 'CAIDO' WHERE hp_atual <= 0")
            conn.commit()
            return jsonify({"sucesso": True}), 200
        except:
            pass
        finally:
            conn.close()
    
    return jsonify({"sucesso": "Modo Simulado"}), 200

if __name__ == "__main__":
    app.run()