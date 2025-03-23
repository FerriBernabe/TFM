import sqlite3
import json
from flask import Flask, render_template, request, jsonify
from collections import OrderedDict

app = Flask(__name__)
app.json.sort_keys = False  # Desactivar ordenamiento automático de claves

# Definir el orden deseado de los campos
FIELD_ORDER = [
    "title",  # Primero
    "status_code",
    "request",
    "redirected_url",
    "port",
    "response_text",
    "response_headers"
]

# Función para reorganizar los campos según FIELD_ORDER
def reorder_fields(entry):
    reordered_entry = OrderedDict()
    for field in FIELD_ORDER:
        if field in entry:
            if isinstance(entry[field], dict):  # Convertir diccionarios anidados a JSON
                reordered_entry[field] = json.dumps(entry[field], indent=4)
            else:
                reordered_entry[field] = entry[field]
    # Agregar campos restantes
    for key, value in entry.items():
        if key not in FIELD_ORDER and key not in reordered_entry:
            if isinstance(value, dict):
                reordered_entry[key] = json.dumps(value, indent=4)
            else:
                reordered_entry[key] = value
    return reordered_entry

# Verificar si una entrada contiene la consulta
def contains_query(entry, query):
    query = query.lower()  # Convertir a minúsculas para comparación insensible a mayúsculas
    for value in entry.values():
        if isinstance(value, str) and query in value.lower():  # Comparar cadenas
            return True
        elif isinstance(value, dict):  # Buscar en diccionarios anidados
            for nested_value in value.values():
                if isinstance(nested_value, str) and query in nested_value.lower():
                    return True
    return False

# Ruta principal para mostrar todos los resultados
@app.route('/')
def show_responses():
    conn = sqlite3.connect("../db/web_responses.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT ip, data FROM responses")
    rows = cursor.fetchall()
    conn.close()

    formatted_responses = []
    for ip, data in rows:
        try:
            entries = json.loads(data)
            if isinstance(entries, list):
                for entry in entries:
                    reordered_entry = reorder_fields(entry)
                    formatted_responses.append({"ip": ip, "entry": dict(reordered_entry)})
            else:
                reordered_entry = reorder_fields(entries)
                formatted_responses.append({"ip": ip, "entry": dict(reordered_entry)})
        except json.JSONDecodeError:
            pass

    return render_template("index.html", responses=formatted_responses)

# Ruta para buscar coincidencias en la base de datos
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    conn = sqlite3.connect("../db/web_responses.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ip, data 
        FROM responses 
        WHERE ip LIKE ? OR data LIKE ?
    """, (f"%{query}%", f"%{query}%"))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for ip, data in rows:
        try:
            entries = json.loads(data)
            if isinstance(entries, list):
                for entry in entries:
                    if contains_query(entry, query):  # Verificar si la entrada contiene la consulta
                        reordered_entry = reorder_fields(entry)
                        results.append({"ip": ip, "entry": dict(reordered_entry)})
            else:
                if contains_query(entries, query):  # Verificar si la entrada contiene la consulta
                    reordered_entry = reorder_fields(entries)
                    results.append({"ip": ip, "entry": dict(reordered_entry)})
        except json.JSONDecodeError:
            pass

    return jsonify(results)

# Nueva ruta para mostrar todos los registros
@app.route('/all')
def all_responses():
    conn = sqlite3.connect("../db/web_responses.db")
    cursor = conn.cursor()

    cursor.execute("SELECT ip, data FROM responses")
    rows = cursor.fetchall()
    conn.close()

    results = []
    for ip, data in rows:
        try:
            entries = json.loads(data)
            if isinstance(entries, list):
                for entry in entries:
                    reordered_entry = reorder_fields(entry)
                    results.append({"ip": ip, "entry": dict(reordered_entry)})
            else:
                reordered_entry = reorder_fields(entries)
                results.append({"ip": ip, "entry": dict(reordered_entry)})
        except json.JSONDecodeError:
            pass

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)