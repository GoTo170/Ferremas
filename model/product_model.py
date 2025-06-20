import sqlite3

def listar_productos():
    conn = sqlite3.connect("ferremas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos")
    filas = cursor.fetchall()
    conn.close()

    productos = []
    for fila in filas:
        productos.append({
            "codigo": fila[0],
            "nombre": fila[1],
            "descripcion": fila[2],
            "stock": fila[3],
            "valor": fila[4],
            "imagen": fila[5]
        })
    return productos

def obtener_producto_por_codigo(codigo):
    conn = sqlite3.connect("ferremas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE codigo = ?", (codigo,))
    fila = cursor.fetchone()
    conn.close()

    if fila:
        return {
            "codigo": fila[0],
            "nombre": fila[1],
            "descripcion": fila[2],
            "stock": fila[3],
            "valor": fila[4],
            "imagen": fila[5]
        }
    return None

def actualizar_stock(codigo, cantidad):
    conn = sqlite3.connect("ferremas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM productos WHERE codigo = ?", (codigo,))
    fila = cursor.fetchone()

    if fila and fila[0] >= cantidad:
        nuevo_stock = fila[0] - cantidad
        cursor.execute("UPDATE productos SET stock = ? WHERE codigo = ?", (nuevo_stock, codigo))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False