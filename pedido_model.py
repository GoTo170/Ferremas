import sqlite3

def inicializar_base_datos():
    """Crea las tablas necesarias para los pedidos si no existen"""
    conn = sqlite3.connect("ferremas.db")
    cursor = conn.cursor()
    
    # Tabla de pedidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id_pedido INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_nombre TEXT NOT NULL,
            cliente_email TEXT NOT NULL,
            total INTEGER NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            fecha_pedido DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de productos en pedidos (relación muchos a muchos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos_productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pedido INTEGER,
            codigo_producto TEXT,
            nombre_producto TEXT,
            cantidad INTEGER,
            valor INTEGER,
            FOREIGN KEY (id_pedido) REFERENCES pedidos (id_pedido)
        )
    ''')
    
    # Tabla de acciones de pedidos (para seguimiento)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos_acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pedido INTEGER,
            usuario_id TEXT,
            accion TEXT,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_pedido) REFERENCES pedidos (id_pedido)
        )
    ''')
    
    conn.commit()
    conn.close()

def crear_pedido(cliente_nombre, cliente_email, productos_carrito, total):
    """
    Crea un nuevo pedido
    productos_carrito: lista de dict con {codigo, nombre, cantidad, valor}
    """
    try:
        conn = sqlite3.connect("ferremas.db")
        cursor = conn.cursor()
        
        # Insertar pedido principal
        cursor.execute('''
            INSERT INTO pedidos (cliente_nombre, cliente_email, total, estado)
            VALUES (?, ?, ?, 'pendiente')
        ''', (cliente_nombre, cliente_email, total))
        
        id_pedido = cursor.lastrowid
        
        # Insertar productos del pedido
        for producto in productos_carrito:
            cursor.execute('''
                INSERT INTO pedidos_productos 
                (id_pedido, codigo_producto, nombre_producto, cantidad, valor)
                VALUES (?, ?, ?, ?, ?)
            ''', (id_pedido, producto['codigo'], producto['nombre'], 
                  producto['cantidad'], producto['valor']))
        
        conn.commit()
        return id_pedido
        
    except Exception as e:
        print(f"Error al crear pedido: {e}")
        return None
    finally:
        conn.close()

def obtener_pedidos_por_estado(estado):
    conn = sqlite3.connect("ferremas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE estado = ?", (estado,))
    filas = cursor.fetchall()
    conn.close()

    pedidos = []
    for fila in filas:
        pedidos.append({
            "id_pedido": fila[0],
            "cliente_nombre": fila[1],
            "cliente_email": fila[2],
            "total": fila[3],
            "estado": fila[4],
            "fecha_pedido": fila[5]
        })
    return pedidos


def obtener_pedidos_pendientes():
    """Obtiene todos los pedidos pendientes o pagados"""
    try:
        conn = sqlite3.connect("ferremas.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id_pedido, cliente_nombre, cliente_email, total, fecha_pedido, estado
            FROM pedidos 
            WHERE estado IN ('pendiente', 'pagado')
            ORDER BY fecha_pedido DESC
        ''')
        
        pedidos = []
        for row in cursor.fetchall():
            pedidos.append({
                'id_pedido': row[0],
                'cliente_nombre': row[1],
                'cliente_email': row[2],
                'total': row[3],
                'fecha_pedido': row[4],
                'estado': row[5]
            })
        
        return pedidos
        
    except Exception as e:
        print(f"Error al obtener pedidos pendientes: {e}")
        return []
    finally:
        conn.close()

def obtener_productos_pedido(id_pedido):
    """Obtiene los productos de un pedido específico"""
    try:
        conn = sqlite3.connect("ferremas.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT codigo_producto, nombre_producto, cantidad, valor
            FROM pedidos_productos
            WHERE id_pedido = ?
        ''', (id_pedido,))
        
        productos = []
        for row in cursor.fetchall():
            productos.append({
                'codigo': row[0],
                'nombre': row[1],
                'cantidad': row[2],
                'valor': row[3]
            })
        
        return productos
        
    except Exception as e:
        print(f"Error al obtener productos del pedido: {e}")
        return []
    finally:
        conn.close()

def actualizar_estado_pedido(id_pedido, nuevo_estado):
    """Actualiza el estado de un pedido"""
    try:
        conn = sqlite3.connect("ferremas.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE pedidos 
            SET estado = ? 
            WHERE id_pedido = ?
        ''', (nuevo_estado, id_pedido))
        
        conn.commit()
        return cursor.rowcount > 0  # Retorna True si se actualizó alguna fila
        
    except Exception as e:
        print(f"Error al actualizar estado del pedido: {e}")
        return False
    finally:
        conn.close()

def registrar_accion_pedido(id_pedido, usuario_id, accion):
    """Registra una acción realizada en un pedido"""
    try:
        conn = sqlite3.connect("ferremas.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO pedidos_acciones (id_pedido, usuario_id, accion)
            VALUES (?, ?, ?)
        ''', (id_pedido, usuario_id, accion))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error al registrar acción del pedido: {e}")
        return False
    finally:
        conn.close()

def obtener_pedido_por_id(id_pedido):
    """Obtiene un pedido específico por su ID"""
    try:
        conn = sqlite3.connect("ferremas.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id_pedido, cliente_nombre, cliente_email, total, fecha_pedido, estado
            FROM pedidos 
            WHERE id_pedido = ?
        ''', (id_pedido,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id_pedido': row[0],
                'cliente_nombre': row[1],
                'cliente_email': row[2],
                'total': row[3],
                'fecha_pedido': row[4],
                'estado': row[5]
            }
        return None
        
    except Exception as e:
        print(f"Error al obtener pedido: {e}")
        return None
    finally:
        conn.close()

# Función para insertar pedidos de prueba (opcional)
def insertar_pedidos_prueba():
    """Inserta algunos pedidos de prueba para testing"""
    try:
        # Primer pedido de prueba
        productos_prueba1 = [
            {'codigo': 'P002', 'nombre': 'Martillo Stanley', 'cantidad': 2, 'valor': 8990},
            {'codigo': 'P001', 'nombre': 'Taladro Bosch', 'cantidad': 1, 'valor': 49990}
        ]
        total1 = (8990 * 2) + (49990 * 1)  # 67970
        crear_pedido("Juan Pérez", "juan@email.com", productos_prueba1, total1)
        
        # Segundo pedido de prueba
        productos_prueba2 = [
            {'codigo': 'P003', 'nombre': 'Caja de Tornillos Tenz', 'cantidad': 1, 'valor': 150000}
        ]
        total2 = 150000 * 1  # 150000
        crear_pedido("María González", "maria@email.com", productos_prueba2, total2)
        
        # Tercer pedido de prueba
        productos_prueba3 = [
            {'codigo': 'P001', 'nombre': 'Taladro Bosch', 'cantidad': 1, 'valor': 49990},
            {'codigo': 'P003', 'nombre': 'Caja de Tornillos Tenz', 'cantidad': 2, 'valor': 150000}
        ]
        total3 = (49990 * 1) + (150000 * 2)  # 349990
        crear_pedido("Carlos Ramírez", "carlos@email.com", productos_prueba3, total3)
        
        print("Pedidos de prueba insertados correctamente")
        
    except Exception as e:
        print(f"Error al insertar pedidos de prueba: {e}")

# Función adicional para integrar con el sistema de productos existente
def crear_pedido_desde_productos(cliente_nombre, cliente_email, codigos_productos, cantidades):
    """
    Crea un pedido obteniendo la información de productos desde la base de datos
    codigos_productos: lista de códigos de productos
    cantidades: lista de cantidades correspondientes a cada producto
    """
    # Cambiar esta línea:
    # from productos_model import obtener_producto_por_codigo, actualizar_stock
    # Por esta:
    from model.product_model import obtener_producto_por_codigo
    
    try:
        productos_carrito = []
        total = 0
        
        # Verificar disponibilidad y preparar carrito
        for i, codigo in enumerate(codigos_productos):
            producto = obtener_producto_por_codigo(codigo)
            cantidad = cantidades[i]
            
            if not producto:
                print(f"Producto {codigo} no encontrado")
                return None
                
            if producto['stock'] < cantidad:
                print(f"Stock insuficiente para {producto['nombre']}. Stock disponible: {producto['stock']}")
                return None
            
            productos_carrito.append({
                'codigo': codigo,
                'nombre': producto['nombre'],
                'cantidad': cantidad,
                'valor': producto['valor']
            })
            
            total += producto['valor'] * cantidad
        
        # Crear el pedido
        id_pedido = crear_pedido(cliente_nombre, cliente_email, productos_carrito, total)
        
        if id_pedido:
            # Aquí podrías actualizar el stock si tu product_model tiene esa función
            print(f"Pedido {id_pedido} creado exitosamente")
        
        return id_pedido
        
    except Exception as e:
        print(f"Error al crear pedido desde productos: {e}")
        return None
