import sqlite3

# Crear/conectar a la base de datos
conn = sqlite3.connect("ferremas.db")
cursor = conn.cursor()

# Crear tabla de usuarios con campo de rol
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    rol TEXT NOT NULL
)
""")

# Crear tabla de productos
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    codigo TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    stock INTEGER NOT NULL,
    valor INTEGER NOT NULL,
    imagen TEXT
)
""")

# usuarios definidos
usuarios = [
    ("Juan", "cliente1@gmail.com", "Cliente.01", "cliente"),
    ("Diego", "admin1@gmail.com", "Admin.01", "administrador"),
    ("Antonella", "admin2@gmail.com", "Admin.02", "administrador"),
    ("Carlos", "vendedor1@gmail.com", "Vendedor.01", "vendedor"),
    ("Maximiliano", "vendedor2@gmail.com", "Vendedor.02", "vendedor"),
    ("Javier", "bodeguero1@gmail.com", "Bodeguero.01", "bodeguero"),
    ("Gianinna", "bodeguero2@gmail.com", "Bodeguero.02", "bodeguero"),
]

cursor.executemany("""
INSERT OR IGNORE INTO usuarios (name, email, password, rol) VALUES (?, ?, ?, ?)
""", usuarios)

# Insertar productos de ejemplo
productos = [
    ("P001", "Taladro Bosch", "Taladro percutor Bosch 500W.", 10, 49990, "taladro_bosch.jpg"),
    ("P002", "Martillo Stanley", "Martillo de carpintero 16oz Stanley.", 25, 8990, "martillo_stanley.jpg"),
    ("P003", "Caja de Tornillos Tenz", "Paquete con 100 tornillos de alta resistencia.", 50, 150000, "tornillos_tenz.jpg")
]

cursor.executemany("INSERT OR IGNORE INTO productos VALUES (?, ?, ?, ?, ?, ?)", productos)

conn.commit()
conn.close()
print("Base de datos creada con éxito.")