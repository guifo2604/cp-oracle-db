import os
import oracledb
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# --- Configuração Inicial ---
load_dotenv()
app = Flask(__name__)
CORS(app)

# --- Dados de Teste (Fallback para Apresentação) ---
# Usamos uma lista global para que o dano persista enquanto o servidor estiver rodando
herois_simulados = [
    {"id": 1, "nome": "Galaad (Simulado)", "classe": "Paladino", "hp_atual": 120, "hp_max": 120, "status": "ATIVO"},
    {"id": 2, "nome": "Morgana (Simulado)", "classe": "Maga", "hp_atual": 70, "hp_max": 70, "status": "ATIVO"}
]

def get_connection():
    """Tenta conectar ao Oracle usando variáveis de ambiente da Vercel"""
    user = os.environ.get("DB_USER")
    pw = os.environ.get("DB_PASSWORD")
    dsn = os.environ.get("DB_DSN")
    
    if not user or not pw:
        print("ERRO: Credenciais ausentes nas variáveis de ambiente.")
        return None
        
    try:
        # Modo Thin do oracledb com timeout para evitar travamento (Erro 504/500)
        return oracledb.connect(
            user=user, 
            password=pw, 
            dsn=dsn, 
            expire_time=1  # Tempo de resposta curto para o banco
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
        </style>
    </head>
    <body>
        <header><h1>⚔️ SISTEMA DE BATALHA</h1></header>
        <div class="container">
            <button onclick="processarTurno()" id="btn-turno">AVANÇAR TURNO (DANO DE NÉVOA)</button>
            <div id="lista-herois"></div>
        </div>
        <script>
            async function carregar() {
                const res = await fetch('/herois');
                const dados = await res.json();
                document.getElementById('lista-herois').innerHTML = dados.map(h => `
                    <div class="card ${h.status === 'CAIDO' ? 'caido' : ''}">
                        <strong>${h.nome}</strong> (${h.classe})<br>
                        <div class="hp-bg"><div class="hp-bar" style="width: ${(h.hp_atual/h.hp_max)*100}%"></div></div>
                        <small>HP: ${h.hp_atual}/${h.hp_max} - ${h.status}</small>
                    </div>
                `).join('');
            }
            async function processarTurno() {
                const btn = document.getElementById('btn-turno');
                btn.innerText = "PROCESSANDO..."; btn.disabled = true;
                await fetch('/proximo-turno', { method: 'POST' });
                await carregar();
                btn.innerText = "AVANÇAR TURNO (DANO DE NÉVOA)"; btn.disabled = false;
            }
            carregar();
        </script>
    </body></html>
    """

# --------------------------------
# API: LISTAR HERÓIS
# --------------------------------
@app.route("/herois", methods=["GET"])
def api_listar_herois():
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id_heroi, nome, classe, hp_atual, hp_max, status FROM TB_HEROIS")
            dados = cursor.fetchall()
            return jsonify([{"id": h[0], "nome": h[1], "classe": h[2], "hp_atual": h[3], "hp_max": h[4], "status": h[5]} for h in dados]), 200
        except Exception as e:
            print(f"Erro na query: {e}")
        finally:
            conn.close()

    # Fallback: Se o banco da FIAP não responder, envia os simulados
    return jsonify(herois_simulados), 200

# --------------------------------
# API: PRÓXIMO TURNO
# --------------------------------
@app.route("/proximo-turno", methods=["POST"])
def api_proximo_turno():
    conn = get_connection()
    sucesso_banco = False
    
    if conn:
        try:
            cursor = conn.cursor()
            # Tenta atualizar o banco real
            cursor.execute("UPDATE TB_HEROIS SET hp_atual = hp_atual - 15 WHERE status = 'ATIVO'")
            cursor.execute("UPDATE TB_HEROIS SET status = 'CAIDO' WHERE hp_atual <= 0")
            conn.commit()
            sucesso_banco = True
        except Exception as e:
            print(f"Erro no update: {e}")
        finally:
            conn.close()

    # Sincroniza os simulados (para garantir que a barra de vida desça na apresentação)
    for h in herois_simulados:
        if h["status"] == "ATIVO":
            h["hp_atual"] = max(0, h["hp_atual"] - 15)
            if h["hp_atual"] <= 0:
                h["status"] = "CAIDO"

    status_msg = "Real" if sucesso_banco else "Simulado (Banco Offline)"
    return jsonify({"status": status_msg}), 200

if __name__ == "__main__":
    app.run()