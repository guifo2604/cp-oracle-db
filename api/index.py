import os
import oracledb
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
# --- Configuração Inicial ---
load_dotenv()
app = Flask(__name__)
CORS(app)

# --- Conexão com o Banco ---
def get_connection():
    return oracledb.connect(
        user=os.getenv("DBUSER"),
        password=os.getenv("DBPASSWORD"),
        dsn=os.getenv("DBDSN")
    )


# --------------------------------
# ROTA TESTE
# --------------------------------
@app.route("/")
def hello():
    return "Servidor funcionando"


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