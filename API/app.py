import sqlite3, re
from flask import Flask, request, jsonify, g
from flask_cors import CORS, cross_origin

DATABASE = 'phab.db'

app = Flask(__name__)
CORS(app)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def insert_db(query, args=()):
    db = get_db()
    db.execute(query, args)
    db.commit()

@app.route('/')
def get_all_phabs():
    phab_records = query_db('SELECT * FROM phab')
    phab_list = [dict(ix) for ix in phab_records]
    return jsonify(phab_list)

#### other functions

def check_format(ern):
    # Define the regex pattern to match "ern" followed by exactly 4 digits
    pattern = r'^ern\d{4}$'
    
    # Use re.match to check if the pattern matches the entire string
    if re.match(pattern, ern):
        return True
    else:
        return False
    

#### API routes and business
@app.route('/activate', methods=['POST'])
def activate_phab():
    data = request.json
    ern = data.get('ern')
    if not ern:
        return jsonify({"error": "ERN is required"}), 400

    phab = query_db('SELECT * FROM phab WHERE ern = ?', [ern], one=True)
    if phab:
        if phab['is_active']:
            return jsonify({"error": "phab is already activated"}), 400
        else:
            insert_db('UPDATE phab SET is_active = 1 WHERE ern = ?', [ern])
            return jsonify({"message": "phab wit"+ern+" is active now"}), 200

    else:
        if check_format(ern):
            insert_db('INSERT INTO phab (ern, is_active) VALUES (?, 1)', [ern])
            return jsonify({"message": "phab activated successfully"}), 200
        else:
            return jsonify({"message": "This phab ern is not correct!"}), 200
    

@app.route('/deactivate', methods=['POST'])
def deactivate_phab():
    data = request.json
    ern = data.get('ern')
    if not ern:
        return jsonify({"error": "ERN is required"}), 400

    phab = query_db('SELECT * FROM phab WHERE ern = ?', [ern], one=True)
    if phab:
        if phab['is_active']:
            insert_db('UPDATE phab SET is_active = 0 WHERE ern = ?', [ern])
            return jsonify({"message": "phab wit"+ern+" is not active now"}), 200
        else:
            return jsonify({"error": "phab is already deactivated"}), 400           

    else:
        # if check_format(ern):
        #     insert_db('INSERT INTO phab (ern, is_active) VALUES (?, 1)', [ern])
        #     return jsonify({"message": "phab activated successfully"}), 200
        # else:
        return jsonify({"message": "This phab ern is not correct!"}), 200
    




@app.route('/lend', methods=['POST'])
def lend_phab():
    data = request.json
    phab_id = data.get('phab_id')
    friend_id = data.get('friend_id')
    if not all([phab_id, friend_id]):
        return jsonify({"error": "phab ID and Friend ID are required"}), 400

    phab = query_db('SELECT * FROM phab WHERE id = ?', [phab_id], one=True)
    if phab and phab['is_active'] and not phab['lent_to_id']:
        insert_db('UPDATE phab SET lent_to_id = ? WHERE id = ?', [friend_id, phab_id])
        return jsonify({"message": "phab lent successfully"}), 200
    else:
        return jsonify({"error": "phab cannot be lent"}), 400

# @app.route('/return', methods=['POST'])
# def return_phab():
#     data = request.json
#     phab_id = data.get('phab_id')
#     if not phab_id:
#         return jsonify({"error": "phab ID is required"}), 400

#     phab = query_db('SELECT * FROM phab WHERE id = ?', [phab_id], one=True)
#     if phab and phab['lent_to_id']:
#         insert_db('UPDATE phab SET lent_to_id = NULL WHERE id = ?', [phab_id])
#         return jsonify({"message": "phab returned successfully"}), 200
#     else:
#         return jsonify({"error": "phab was not lent"}), 400


@app.route('/return', methods=['POST'])
def returnPhAB():
    data = request.get_json()  # Obtenim les dades JSON enviades amb la petició
    phab_id = data['phab_id']
    
    # Connectem a la base de dades
    # conn = sqlite3.connect('phab.db')
    # cursor = conn.cursor()
    
    # Executem la consulta per obtenir la fila basada en l'ID
    # cursor.execute("SELECT * FROM phab WHERE id = ?", (phab_id,))
    # row = cursor.fetchone()
    row =  query_db('SELECT * FROM phab WHERE id = ?', [phab_id], one=True)
    
    # Tanquem la connexió a la base de dades
    # conn.close()
    
    # Comprovem si hem trobat una fila
    if row:
        # Retornem la fila com a JSON
        return jsonify({
            'id': row[0],
            'ern': row[1],
            'is_active': bool(row[2]),
            'owner_id': row[3],
            'lent_to_id': row[4]
        })
    else:
        # Retornem un missatge d'error si no s'ha trobat cap fila
        return jsonify({'error': 'No record found'}), 404


if __name__ == '__main__':
    init_db()  # Ensure the database and tables are created
    app.run(port=5000,debug=True)
