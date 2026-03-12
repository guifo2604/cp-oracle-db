import os
import oracledb
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

def get_connection():
    user = os.environ.get("DB_USER")
    pw = os.environ.get("DB_PASSWORD")
    dsn = os.environ.get("DB_DSN")
    if not user or not pw: return None
    try:
        return oracledb.connect(user=user, password=pw, dsn=dsn, expire_time=1)
    except: return None

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
            header { width: 100%; padding: 20px; text-align: center; background: #1f1f1f; }
            .container { width: 90%; max-width: 800px; margin-top: 30px; }
            .btn-group { display: flex; gap: 10px; margin-bottom: 30px; }
            button { flex: 1; padding: 15px; font-weight: bold; border-radius: 5px; cursor: pointer; border: none; text-transform: uppercase; }
            .btn-turno { background: var(--sec); color: #000; }
            .btn-reset { background: #444; color: #fff; }
            .btn-reset:hover { background: var(--danger); }
            #lista-herois { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
            .card { background: var(--card); padding: 20px; border-radius: 10px; border-left: 5px solid var(--primary); }
            .card.caido { border-left-color: var(--danger); opacity: 0.6; filter: grayscale(1); }
            .hp-bg { background: #333; height: 10px; border-radius: 5px; margin: 10px 0; overflow: hidden; }
            .hp-bar { background: linear-gradient(90deg, #ff4b2b, #ff416c); height: 100%; transition: width 0.5s; }
        </style>
    </head>
    <body onload="carregar()">
        <header><h1>⚔️ SISTEMA DE BATALHA</h1></header>
        <div class="container">
            <div class="btn-group">
                <button onclick="processarTurno()" id="btn-turno" class="btn-turno">⚔️ Avançar Turno</button>
                <button onclick="resetarBanco()" id="btn-reset" class="btn-reset">🔄 Resetar Banco</button>
            </div>
            <div id="lista-herois">Buscando dados...</div>
        </div>
        <script>
            async function carregar() {
                try {
                    const res = await fetch('/herois');
                    const dados = await res.json();
                    const container = document.getElementById('lista-herois');
                    if (dados.erro) { container.innerHTML = `<p style="color:red">❌ ${dados.erro}</p>`; return; }
                    container.innerHTML = dados.map(h => `
                        <div class="card ${h.status === 'CAIDO' ? 'caido' : ''}">
                            <strong>${h.nome}</strong> (${h.classe})<br>
                            <div class="hp-bg"><div class="hp-bar" style="width: ${(h.hp_atual/h.hp_max)*100}%"></div></div>
                            <small>HP: ${h.hp_atual}/${h.hp_max} - ${h.status}</small>
                        </div>
                    `).join('');
                } catch (e) { document.getElementById('lista-herois').innerHTML = '❌ Erro de conexão'; }
            }

            async function processarTurno() {
                const btn = document.getElementById('btn-turno');
                btn.innerText = "...";
                await fetch('/proximo-turno', { method: 'POST' });
                await carregar();
                btn.innerText = "⚔️ Avançar Turno";
            }

            async function resetarBanco() {
                if(!confirm("Deseja realmente apagar e recriar a tabela?")) return;
                const btn = document.getElementById('btn-reset');
                btn.innerText = "RESETANDO...";
                await fetch('/reset', { method: 'POST' });
                await carregar();
                btn.innerText = "🔄 Resetar Banco";
            }
        </script>
    </body></html>
    """

@app.route("/herois")
def api_listar_herois():
    conn = get_connection()
    if not conn: return jsonify({"erro": "Banco desconectado"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_heroi, nome, classe, hp_atual, hp_max, status FROM TB_HEROIS ORDER BY id_heroi")
        dados = cursor.fetchall()
        return jsonify([{"id": h[0], "nome": h[1], "classe": h[2], "hp_atual": h[3], "hp_max": h[4], "status": h[5]} for h in dados]), 200
    except: return jsonify({"erro": "Tabela não encontrada. Clique em Reset."}), 200
    finally: conn.close()

@app.route("/proximo-turno", methods=["POST"])
def api_proximo_turno():
    conn = get_connection()
    if not conn: return jsonify({"erro": "Erro de conexão"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE TB_HEROIS SET hp_atual = hp_atual - 15 WHERE status = 'ATIVO'")
        cursor.execute("UPDATE TB_HEROIS SET status = 'CAIDO' WHERE hp_atual <= 0")
        conn.commit()
        return jsonify({"sucesso": True}), 200
    except Exception as e: return jsonify({"erro": str(e)}), 500
    finally: conn.close()

@app.route("/reset", methods=["POST"])
def api_reset():
    conn = get_connection()
    if not conn: return jsonify({"erro": "Erro de conexão"}), 500
    try:
        cursor = conn.cursor()
        
        # 1. Tenta dropar a tabela (se não existir, o except captura e ignora)
        try:
            cursor.execute("DROP TABLE TB_HEROIS CASCADE CONSTRAINTS")
        except:
            pass
        
        # 2. Cria a tabela novamente
        cursor.execute("""
            CREATE TABLE TB_HEROIS (
                id_heroi NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                nome VARCHAR2(50),
                classe VARCHAR2(20),
                hp_atual NUMBER,
                hp_max NUMBER,
                status VARCHAR2(20) DEFAULT 'ATIVO'
            )
        """)
        
        # 3. Insere os dados iniciais
        inserts = [
            ("Artorias", "GUERREIRO", 100, 100),
            ("Sif", "LADRÃO", 80, 80),
            ("Gwyn", "MAGO", 60, 60)
        ]
        
        for nome, classe, hp, hpm in inserts:
            cursor.execute("INSERT INTO TB_HEROIS (nome, classe, hp_atual, hp_max) VALUES (:1, :2, :3, :4)", (nome, classe, hp, hpm))
        
        conn.commit()
        return jsonify({"sucesso": "Tabela reiniciada"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run()