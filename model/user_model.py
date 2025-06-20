import sqlite3

def verificar_usuario(name, email, password):
    conn = sqlite3.connect("ferremas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE name = ? email = ? AND password = ?", (name, email, password))
    usuario = cursor.fetchone()
    conn.close()
    return usuario is not None