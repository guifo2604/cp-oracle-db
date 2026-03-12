from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import oracledb
from dotenv import load_dotenv
from flask_cors import CORS
# --- Configuração Inicial ---
load_dotenv()
app = Flask(__name__)
CORS(app)

# --- Conexão com o Banco ---
def get_connection():
    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn=os.getenv("DB_DSN")
    )


# --------------------------------
# ROTA TESTE
# --------------------------------
@app.route("/")
def index():
    return """
    <!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hero Manager Pro</title>
    <style>
        :root {
            --bg-color: #121212;
            --card-bg: #1e1e1e;
            --primary: #bb86fc;
            --secondary: #03dac6;
            --danger: #cf6679;
            --text: #e1e1e1;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }

        header {
            width: 100%;
            padding: 2rem 0;
            text-align: center;
            background: linear-gradient(180deg, #1f1f1f 0%, var(--bg-color) 100%);
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            margin-bottom: 2rem;
        }

        h1 { margin: 0; letter-spacing: 2px; color: var(--primary); }

        .container { width: 90%; max-width: 1000px; }

        .controls {
            display: flex;
            justify-content: center;
            margin-bottom: 2rem;
        }

        button {
            background-color: var(--secondary);
            color: #000;
            border: none;
            padding: 12px 24px;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            transition: transform 0.2s, background-color 0.2s;
            text-transform: uppercase;
        }

        button:hover {
            background-color: #01bca9;
            transform: scale(1.05);
        }

        #lista-herois {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }

        .heroi-card {
            background-color: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid var(--primary);
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }

        .heroi-card.caido {
            border-left-color: var(--danger);
            opacity: 0.7;
            filter: grayscale(0.8);
        }

        .info { margin-bottom: 15px; }
        .nome { font-size: 1.2rem; font-weight: bold; display: block; }
        .classe { font-size: 0.9rem; color: #aaa; }

        .hp-container {
            background: #333;
            border-radius: 10px;
            height: 12px;
            width: 100%;
            overflow: hidden;
            margin: 10px 0;
        }

        .hp-bar {
            height: 100%;
            background: linear-gradient(90deg, #ff4b2b, #ff416c);
            transition: width 0.5s ease-in-out;
        }

        .status-badge {
            font-size: 0.7rem;
            padding: 4px 8px;
            border-radius: 4px;
            background: #333;
            float: right;
        }
    </style>
</head>
<body>

    <header>
        <h1>SISTEMA DE BATALHA</h1>
    </header>

    <div class="container">
        <div class="controls">
            <button onclick="processarTurno()">⚔️ Avançar Turno (Dano de Névoa)</button>
        </div>
        
        <div id="lista-herois">
            </div>
    </div>

    <script>
        const API_URL = "";

        async function carregarHerois() {
            try {
                const response = await fetch(`${API_URL}/herois`);
                const herois = await response.json();
                
                const container = document.getElementById('lista-herois');
                container.innerHTML = herois.map(h => {
                    const isCaido = h.status === 'CAIDO';
                    const hpPercent = Math.max(0, (h.hp_atual / h.hp_max) * 100);
                    
                    return `
                        <div class="heroi-card ${isCaido ? 'caido' : ''}">
                            <span class="status-badge">${h.status}</span>
                            <div class="info">
                                <span class="nome">${h.nome}</span>
                                <span class="classe">${h.classe}</span>
                            </div>
                            <div class="hp-container">
                                <div class="hp-bar" style="width: ${hpPercent}%"></div>
                            </div>
                            <div style="font-size: 0.8rem; text-align: right;">
                                HP: ${h.hp_atual} / ${h.hp_max}
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error("Erro ao carregar:", e);
            }
        }

        async function processarTurno() {
            const btn = document.querySelector('button');
            btn.innerText = "Processando...";
            btn.disabled = true;

            try {
                await fetch(`${API_URL}/proximo-turno`, { method: 'POST' });
                await carregarHerois();
            } finally {
                btn.innerText = "⚔️ Avançar Turno (Dano de Névoa)";
                btn.disabled = false;
            }
        }

        carregarHerois();
    </script>
</body>
</html>
    """

@app.route("/<path:path>")
def static_files(path):
    # Rota para carregar CSS, JS ou imagens que estejam na static
    return send_from_directory(app.static_folder, path)

# --- Mantenha suas rotas /herois e /proximo-turno aqui embaixo ---


# --------------------------------
# LISTAR HERÓIS
# --------------------------------
@app.route("/herois", methods=["GET"])
def api_listar_herois():

    connection = get_connection()
    if not connection:
        return jsonify({"erro": "Falha na conexão com o banco"}), 500

    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT id_heroi, nome, classe, hp_atual, hp_max, status
            FROM TB_HEROIS
        """)

        dados = cursor.fetchall()

        herois = []
        for h in dados:
            herois.append({
                "id": h[0],
                "nome": h[1],
                "classe": h[2],
                "hp_atual": h[3],
                "hp_max": h[4],
                "status": h[5]
            })

        return jsonify(herois), 200

    except oracledb.DatabaseError as e:
        return jsonify({"erro": f"Erro de banco de dados: {e}"}), 500

    finally:
        cursor.close()
        connection.close()


# --------------------------------
# PROCESSAR PRÓXIMO TURNO
# --------------------------------
@app.route("/proximo-turno", methods=["POST"])
def api_proximo_turno():

    connection = get_connection()
    if not connection:
        return jsonify({"erro": "Falha na conexão com o banco"}), 500

    cursor = connection.cursor()

    try:

        plsql = """
        DECLARE
            v_dano_nevoa NUMBER := 15;

            CURSOR c_herois IS
                SELECT id_heroi, hp_atual
                FROM TB_HEROIS
                WHERE status = 'ATIVO';

        BEGIN

            FOR r IN c_herois LOOP

                UPDATE TB_HEROIS
                SET hp_atual = hp_atual - v_dano_nevoa
                WHERE id_heroi = r.id_heroi;

                UPDATE TB_HEROIS
                SET status = 'CAIDO'
                WHERE id_heroi = r.id_heroi
                AND hp_atual <= 0;

            END LOOP;

            COMMIT;

        END;
        """

        cursor.execute(plsql)
        connection.commit()

        return jsonify({"sucesso": "Turno processado com sucesso"}), 200

    except oracledb.DatabaseError as e:
        connection.rollback()
        return jsonify({"erro": f"Erro de banco de dados: {e}"}), 500

    finally:
        cursor.close()
        connection.close()


# --------------------------------
# RODAR SERVIDOR
# --------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)