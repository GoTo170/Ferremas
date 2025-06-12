import http.server
import socketserver
import urllib.parse
import urllib.request
import json
import os
import sqlite3
import uuid

from model import product_model
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

webpay_options = WebpayOptions(
    commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
    api_key=IntegrationApiKeys.WEBPAY,
    integration_type=IntegrationType.TEST
)

PORT = 8000

# Carrito de prueba
carrito = []

# Cache para tipos de cambio (evitar múltiples llamadas a la API)
exchange_rates_cache = {}
cache_expiry = None

class MyHandler(http.server.SimpleHTTPRequestHandler):

    def get_exchange_rates(self):
        """Obtiene los tipos de cambio desde la API y los cachea por 1 hora"""
        import datetime
        
        global exchange_rates_cache, cache_expiry
        
        # Verificar si el cache sigue válido (1 hora)
        if cache_expiry and datetime.datetime.now() < cache_expiry:
            return exchange_rates_cache
        
        try:
            # API gratuita sin necesidad de registro
            url = "https://api.exchangerate-api.com/v4/latest/CLP"
            
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                
                # Guardar solo las monedas que necesitamos
                exchange_rates_cache = {
                    'CLP': 1.0,  # Base
                    'USD': data['rates'].get('USD', 0.001),
                    'EUR': data['rates'].get('EUR', 0.0009)
                }
                
                # Cache válido por 1 hora
                cache_expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
                
                return exchange_rates_cache
                
        except Exception as e:
            print(f"Error al obtener tipos de cambio: {e}")
            # Valores por defecto en caso de error
            return {
                'CLP': 1.0,
                'USD': 0.001,
                'EUR': 0.0009
            }

    def convert_price(self, price_clp, target_currency):
        """Convierte un precio de CLP a la moneda objetivo"""
        rates = self.get_exchange_rates()
        
        if target_currency not in rates:
            return price_clp
            
        converted_price = price_clp * rates[target_currency]
        
        # Formatear según la moneda
        if target_currency == 'CLP':
            return int(converted_price)
        else:
            return round(converted_price, 2)

    def format_currency(self, amount, currency):
        """Formatea el precio según la moneda"""
        symbols = {
            'CLP': '$',
            'USD': '$',
            'EUR': '€'
        }
        
        if currency == 'CLP':
            return f"{symbols[currency]}{int(amount)}"
        else:
            return f"{symbols[currency]}{amount:.2f}"

    def obtener_datos_sesion(self):
        """Obtiene los datos de sesión del usuario desde las cookies"""
        if "Cookie" in self.headers:
            cookies = self.headers.get("Cookie")
            cookies_dict = {}
            try:
                for cookie in cookies.split(";"):
                    if "=" in cookie:
                        key, value = cookie.strip().split("=", 1)
                        cookies_dict[key] = value
            except Exception as e:
                print("Error al procesar cookies:", e)
                return None

            email = cookies_dict.get("email")
            if email:
                try:
                    conn = sqlite3.connect("ferremas.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, rol FROM usuarios WHERE email = ?", (email,))
                    row = cursor.fetchone()
                    if row:
                        return {"name": row[0], "rol": row[1], "email": email}
                except Exception as e:
                    print("Error al obtener sesión desde DB:", e)
                finally:
                    conn.close()
        return None

    def get_currency_from_cookies(self):
        """Obtiene la moneda seleccionada desde las cookies"""
        if "Cookie" in self.headers:
            cookies = self.headers.get("Cookie")
            for cookie in cookies.split(";"):
                if "=" in cookie:
                    key, value = cookie.strip().split("=", 1)
                    if key == "currency":
                        return value if value in ['CLP', 'USD', 'EUR'] else 'CLP'
        return 'CLP'  # Por defecto

    def do_GET(self):
        if self.path == "/":
            self.path = "view/index.html"

        elif self.path.startswith("/set_currency"):
            """Endpoint para cambiar la moneda"""
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            currency = params.get("currency", ["CLP"])[0]
            
            if currency in ['CLP', 'USD', 'EUR']:
                self.send_response(302)
                self.send_header("Location", "/catalog")
                self.send_header("Set-Cookie", f"currency={currency}; Path=/")
                self.end_headers()
            else:
                self.send_response(400)
                self.end_headers()
            return

        elif self.path.startswith("/login"):
            # Leer la plantilla HTML
            with open("view/login.html", "r", encoding="utf-8") as file:
                html = file.read()

            # Verificar parámetros de éxito o error
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            mensaje_html = ""
            if params.get("registered", ["0"])[0] == "1":
                mensaje_html = '<p style="color:green;">¡Registro exitoso! Ahora puedes iniciar sesión.</p>'
            elif params.get("error", ["0"])[0] == "1":
                mensaje_html = '<p style="color:red;">Correo o contraseña incorrectos.</p>'

            html = html.replace("{{mensaje}}", mensaje_html)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        elif self.path.startswith("/register"):
            with open("view/register.html", "r", encoding="utf-8") as file:
                html = file.read()

            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            error_html = ""
            if params.get("error", ["0"])[0] == "1":
                error_html = '<p style="color:red;">El correo ya está registrado.</p>'
            html = html.replace("{{error}}", error_html)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        elif self.path.startswith("/catalog"):
            print("Entré al /catalog")
            with open("view/catalog.html", "r", encoding="utf-8") as file:
                html = file.read()

            # Obtener moneda seleccionada
            current_currency = self.get_currency_from_cookies()

            # Obtener datos del usuario desde la cookie de sesión
            datos_usuario = self.obtener_datos_sesion()
            print("datos_usuario:", datos_usuario)

            rol_html = ""
            btn_add_product = ""
            btn_admin = ""

            # Obtener mensaje de la URL si existe
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            mensaje = params.get("mensaje", [""])[0]
            mensaje_html = ""
            if mensaje:
                mensaje_html = f'<div class="message success" style="background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; margin: 10px 0;">{urllib.parse.unquote_plus(mensaje)}</div>'

            # Crear selector de moneda
            currency_selector = f'''
            <div class="currency-selector" style="margin: 20px 0; text-align: center;">
                <label for="currency-select" style="margin-right: 10px; font-weight: bold;">Moneda:</label>
                <select id="currency-select" onchange="changeCurrency()" style="padding: 5px 10px; font-size: 14px; border-radius: 5px; border: 1px solid #ccc;">
                    <option value="CLP" {"selected" if current_currency == "CLP" else ""}>Peso Chileno (CLP)</option>
                    <option value="USD" {"selected" if current_currency == "USD" else ""}>Dólar Americano (USD)</option>
                    <option value="EUR" {"selected" if current_currency == "EUR" else ""}>Euro (EUR)</option>
                </select>
            </div>
            <script>
                function changeCurrency() {{
                    var select = document.getElementById('currency-select');
                    var currency = select.value;
                    window.location.href = '/set_currency?currency=' + currency;
                }}
            </script>
            '''

            if datos_usuario:
                rol = datos_usuario.get("rol", "")
                print("Rol del usuario:", rol)
                rol_html = f"<p>Rol: {rol}</p>"

                if rol in ["administrador", "vendedor"]:
                    btn_add_product = '''
                    <div id="add-product-button">
                        <a href="/agregar_producto">
                            <button>Nuevo Producto</button>
                        </a>
                    </div>
                    '''
                if rol == "administrador":
                    btn_admin = '''
                    <div id="admin-button">
                        <a href="/administracion">
                            <button>Administración</button>
                        </a>
                    </div>
                    '''
            else:
                print("No se encontraron datos de sesión. El usuario no está autenticado.")

            # Armar HTML de productos con conversión de moneda
            productos_html = ""
            for producto in product_model.listar_productos():
                ruta_imagen = f"/static/img/{producto['imagen']}"
                
                # Convertir precio a la moneda seleccionada
                precio_original = producto['valor']
                precio_convertido = self.convert_price(precio_original, current_currency)
                precio_formateado = self.format_currency(precio_convertido, current_currency)
                
                productos_html += f"""
                <div class="producto">
                    <img src="{ruta_imagen}" alt="{producto['nombre']}">
                    <h2>{producto['nombre']}</h2>
                    <p class="precio">{precio_formateado}</p>
                    <a href="/product_detail?codigo={producto['codigo']}" class="btn-ver-mas">Ver más</a>
                </div>
                """

            # Insertar contenido dinámico
            html = html.replace("{{productos}}", productos_html)
            html = html.replace("{{rol}}", rol_html)
            html = html.replace("{{btn_add_product}}", btn_add_product)
            html = html.replace("{{btn_admin}}", btn_admin)
            
            # Insertar selector de moneda (buscar un lugar apropiado en el HTML)
            if "{{currency_selector}}" in html:
                html = html.replace("{{currency_selector}}", currency_selector)
            else:
                # Si no existe el placeholder, agregarlo después del body
                html = html.replace("<body>", f"<body>{currency_selector}")
            
            # Agregar el mensaje si existe
            if "{{mensaje}}" in html:
                html = html.replace("{{mensaje}}", mensaje_html)
            else:
                # Si no existe el placeholder, agregarlo después del currency selector
                html = html.replace(currency_selector, f"{currency_selector}{mensaje_html}")

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return
        
        elif self.path == "/administracion":
            datos_usuario = self.obtener_datos_sesion()
            if not datos_usuario or datos_usuario.get("rol") != "administrador":
                self.send_response(303)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            with open("view/administracion.html", "r", encoding="utf-8") as file:
                html = file.read()

            # Construir lista de usuarios
            conn = sqlite3.connect("ferremas.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name, email, rol FROM usuarios")
            usuarios = cursor.fetchall()
            conn.close()

            usuarios_html = ""
            for nombre, email, rol in usuarios:
                usuarios_html += f"""
                <div class="usuario">
                    <strong>{nombre}</strong> ({email}) - {rol}
                    <button onclick="confirmarEliminacion('{email}')">Eliminar</button>
                </div>
                """

            html = html.replace("{{usuarios_html}}", usuarios_html)
            html = html.replace("{{mensaje}}", "")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return
        
        elif self.path.startswith("/eliminar_usuario"):
            # Verificar que el usuario sea administrador
            datos_usuario = self.obtener_datos_sesion()
            if not datos_usuario or datos_usuario.get("rol") != "administrador":
                self.send_response(303)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            email = params.get("email", [""])[0]

            if email:
                try:
                    conn = sqlite3.connect("ferremas.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE email = ?", (email,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print("Error al eliminar usuario:", e)

            self.send_response(303)
            self.send_header("Location", "/administracion")
            self.end_headers()
            return

        
        elif self.path.startswith("/product_detail"): 
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            codigo = params.get("codigo", [""])[0]

            if not codigo:
                self.send_error(400, "Código de producto requerido")
                return

            try:
                producto = product_model.obtener_producto_por_codigo(codigo)

                if producto:
                    with open("view/product_detail.html", "r", encoding="utf-8") as file:
                        html = file.read()

                    # Obtener moneda actual
                    current_currency = self.get_currency_from_cookies()

                    # Ajustar ruta de imagen - verificar si ya tiene la ruta completa
                    if not producto["imagen"].startswith("/static/"):
                        producto["imagen"] = f"/static/img/{producto['imagen']}"

                    # Convertir precio
                    precio_original = producto['valor']
                    precio_convertido = self.convert_price(precio_original, current_currency)
                    precio_formateado = self.format_currency(precio_convertido, current_currency)
                    
                    # Reemplazar variables en el HTML
                    for key, value in producto.items():
                        # Manejar valores None
                        if value is None:
                            value = "No disponible"
                        # Reemplazar precio con el convertido
                        if key == 'valor':
                            html = html.replace(f"{{{{{key}}}}}", precio_formateado)
                        else:
                            html = html.replace(f"{{{{{key}}}}}", str(value))

                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_error(404, "Producto no encontrado")
            except Exception as e:
                print(f"Error al cargar producto: {e}")
                self.send_error(500, "Error interno del servidor")
            return

        elif self.path.startswith("/add_to_cart"):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            codigo = params.get("codigo", [""])[0]

            if codigo:
                # Buscar si el producto ya está en el carrito
                for item in carrito:
                    if item["codigo"] == codigo:
                        item["cantidad"] += 1
                        break
                else:
                    # Si no está, agregarlo
                    carrito.append({"codigo": codigo, "cantidad": 1})

            self.send_response(302)
            self.send_header("Location", "/cart")
            self.end_headers()
            return

        elif self.path.startswith("/cart"):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)

            codigo_sumar = params.get("sumar", [None])[0]
            codigo_restar = params.get("restar", [None])[0]
            codigo_eliminar = params.get("eliminar", [None])[0]

            # Manejar acciones del carrito
            if codigo_sumar:
                for item in carrito:
                    if item["codigo"] == codigo_sumar:
                        item["cantidad"] += 1
                        break

            if codigo_restar:
                for item in carrito:
                    if item["codigo"] == codigo_restar:
                        if item["cantidad"] > 1:
                            item["cantidad"] -= 1
                        break

            if codigo_eliminar:
                carrito[:] = [item for item in carrito if item["codigo"] != codigo_eliminar]

            with open("view/cart.html", "r", encoding="utf-8") as file:
                html = file.read()

            # Obtener moneda actual
            current_currency = self.get_currency_from_cookies()

            productos_html = ""
            total = 0

            if carrito:
                for item in carrito:
                    producto = product_model.obtener_producto_por_codigo(item["codigo"])
                    if producto:
                        # Convertir precios
                        precio_unitario = self.convert_price(producto["valor"], current_currency)
                        subtotal = precio_unitario * item["cantidad"]
                        total += subtotal
                        
                        precio_unitario_formateado = self.format_currency(precio_unitario, current_currency)
                        subtotal_formateado = self.format_currency(subtotal, current_currency)
                        
                        productos_html += f"""
                        <tr>
                            <td class="product-name">{producto['nombre']}</td>
                            <td class="quantity-controls">
                                <span>{item['cantidad']}</span>
                                <a href="/cart?sumar={item['codigo']}" title="Aumentar cantidad">➕</a>
                                <a href="/cart?restar={item['codigo']}" title="Disminuir cantidad">➖</a>
                            </td>
                            <td class="subtotal">{subtotal_formateado}</td>
                            <td class="remove-item">
                                <a href="#" onclick="confirmarEliminacion('{item['codigo']}', '{producto['nombre'].replace("'", "\\'")}'); return false;" title="Eliminar producto">🗑️</a>
                            </td>
                        </tr>
                        """
                mensaje = ""
            else:
                mensaje = "Tu carrito está vacío"

            total_formateado = self.format_currency(total, current_currency)

            html = html.replace("{{productos}}", productos_html)
            html = html.replace("{{total}}", total_formateado)
            html = html.replace("{{mensaje_carrito}}", mensaje)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        elif self.path == "/checkout":
            if not carrito:
                self.send_response(302)
                self.send_header("Location", "/cart")
                self.end_headers()
                return

            # Calcular el total del carrito en CLP (para Webpay)
            total_clp = 0
            for item in carrito:
                producto = product_model.obtener_producto_por_codigo(item["codigo"])
                if producto:
                    subtotal = producto["valor"] * item["cantidad"]  # Precio original en CLP
                    total_clp += subtotal

            # Crear una orden de compra única
            buy_order = uuid.uuid4().hex[:26]
            session_id = str(uuid.uuid4())
            return_url = "http://localhost:8000/confirmacion_pago"

            try:
                # Crear la transacción (siempre en CLP para Webpay)
                tx = Transaction(webpay_options)
                response = tx.create(buy_order, session_id, total_clp, return_url)

                # Redirigir al usuario al formulario de pago de Webpay
                self.send_response(302)
                self.send_header("Location", response['url'] + "?token_ws=" + response['token'])
                self.end_headers()
            except Exception as e:
                print("Error al crear transacción:", e)
                self.send_error(500, "Error al procesar el pago")
            return
        
        elif self.path.startswith("/confirmacion_pago"):
            parsed_url = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_url.query)

            tbk_token = query.get('TBK_TOKEN', [None])[0]
            tbk_orden_compra = query.get('TBK_ORDEN_COMPRA', [None])[0]
            tbk_id_sesion = query.get('TBK_ID_SESION', [None])[0]

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            if tbk_token is None:
                # Pago aprobado
                carrito.clear()  # Vaciar el carrito
                mensaje = "<h1>Pago aprobado</h1><p>¡Gracias por tu compra!</p>"
            else:
                # Pago cancelado
                mensaje = f"<h1>Pago cancelado</h1><p>Orden: {tbk_orden_compra}</p>"

            self.wfile.write(f"""
                <html><body>
                {mensaje}
                <p><a href='/catalog'>Volver al catálogo</a></p>
                </body></html>
            """.encode("utf-8"))
            return
        
        elif self.path.startswith("/agregar_producto"):
            # Verificar permisos
            datos_usuario = self.obtener_datos_sesion()
            if not datos_usuario or datos_usuario.get("rol") not in ["administrador", "vendedor"]:
                self.send_response(303)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            try:
                with open("view/agregar_producto.html", "r", encoding="utf-8") as file:
                    html = file.read()

                # Obtener mensaje de la URL
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                mensaje = params.get("mensaje", [""])[0]
                error = params.get("error", [""])[0]
                
                # Generar mensaje HTML
                mensaje_html = ""
                if mensaje:
                    mensaje_html = f'<div class="message success">{urllib.parse.unquote_plus(mensaje)}</div>'
                elif error:
                    mensaje_html = f'<div class="message error">{urllib.parse.unquote_plus(error)}</div>'
                
                html = html.replace("{{mensaje}}", mensaje_html)

                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            except Exception as e:
                print(f"Error al cargar formulario agregar producto: {e}")
                self.send_error(500, "Error interno del servidor")
            return

        elif self.path.startswith("/static/"):
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        else:
            self.send_error(404)
            return
        
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == "/login":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            fields = urllib.parse.parse_qs(post_data.decode('utf-8'))

            email = fields.get('email', [''])[0]
            password = fields.get('password', [''])[0]

            try:
                conn = sqlite3.connect("ferremas.db")
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM usuarios WHERE email = ? AND password = ?", (email, password))
                usuario_valido = cursor.fetchone()

                if usuario_valido:
                    # Crear una cookie con el email del usuario
                    self.send_response(302)
                    self.send_header("Location", "/catalog")
                    self.send_header("Set-Cookie", f"email={email}; Path=/")
                    self.end_headers()
                else:
                    self.send_response(302)
                    self.send_header("Location", "/login?error=1")
                    self.end_headers()
            except Exception as e:
                print("Error en login:", e)
                self.send_error(500, "Error interno del servidor")
            finally:
                conn.close()

        elif self.path == "/register":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            fields = urllib.parse.parse_qs(post_data.decode('utf-8'))

            nombre = fields.get('nombre', [''])[0]
            email = fields.get('email', [''])[0]
            password = fields.get('password', [''])[0]

            try:
                conn = sqlite3.connect("ferremas.db")
                cursor = conn.cursor()

                # Verificar si ya existe email
                cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
                existente = cursor.fetchone()

                if existente:
                    # Si existe, redirigir con error
                    self.send_response(302)
                    self.send_header("Location", "/register?error=1")
                    self.end_headers()
                else:
                    # Insertar nuevo usuario
                    cursor.execute("INSERT INTO usuarios (name, email, password, rol) VALUES (?, ?, ?, ?)",
                                 (nombre, email, password, 'cliente'))
                    conn.commit()

                    # Redirigir a login con mensaje de éxito
                    self.send_response(302)
                    self.send_header("Location", "/login?registered=1")
                    self.end_headers()
            except Exception as e:
                print("Error al registrar usuario:", e)
                self.send_error(500, "Error interno del servidor")
            finally:
                conn.close()

        elif self.path == "/confirmacion_pago":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            fields = urllib.parse.parse_qs(post_data.decode('utf-8'))
            token = fields.get('token_ws', [''])[0]

            try:
                # Confirmar la transacción
                tx = Transaction(webpay_options)
                result = tx.commit(token)

                # Verificar el resultado de la transacción
                if result['status'] == 'AUTHORIZED':
                    carrito.clear()  # Vaciar el carrito
                    mensaje = "Pago realizado con éxito. Gracias por su compra."
                else:
                    mensaje = "El pago no fue autorizado. Intente nuevamente."
            except Exception as e:
                print("Error al confirmar pago:", e)
                mensaje = "Error al procesar el pago."

            # Mostrar la confirmación
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"""
                <html><body>
                    <h1>{mensaje}</h1>
                    <p><a href='/catalog'>Volver al catálogo</a></p>
                </body></html>
            """.encode("utf-8"))
            return
        
        elif self.path == "/crear_usuario":
            # Verificar permisos de administrador
            datos_usuario = self.obtener_datos_sesion()
            if not datos_usuario or datos_usuario.get("rol") != "administrador":
                self.send_response(303)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            datos = urllib.parse.parse_qs(post_data)

            nombre = datos.get("nombre", [""])[0]
            email = datos.get("email", [""])[0]
            password = datos.get("password", [""])[0]
            rol = datos.get("rol", [""])[0]

            try:
                conn = sqlite3.connect("ferremas.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO usuarios (name, email, password, rol) VALUES (?, ?, ?, ?)",
                              (nombre, email, password, rol))
                conn.commit()
                mensaje = "<p style='color:green;'>Usuario creado exitosamente.</p>"
            except Exception as e:
                print("Error al crear usuario:", e)
                mensaje = "<p style='color:red;'>Error al crear usuario.</p>"
            finally:
                conn.close()

            # Redirigir de vuelta a administración
            self.send_response(302)
            self.send_header("Location", "/administracion")
            self.end_headers()
            return

        elif self.path == "/agregar_producto": 
            # Verificar permisos
            datos_usuario = self.obtener_datos_sesion()
            if not datos_usuario or datos_usuario.get("rol") not in ["administrador", "vendedor"]:
                self.send_response(303)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                fields = urllib.parse.parse_qs(post_data.decode('utf-8'))

                # Obtener y validar campos
                codigo = fields.get('codigo', [''])[0].strip()
                nombre = fields.get('nombre', [''])[0].strip()
                descripcion = fields.get('descripcion', [''])[0].strip()
                imagen = fields.get('imagen', [''])[0].strip()
                
                # Validar campos numéricos
                try:
                    valor = int(fields.get('valor', ['0'])[0]) if fields.get('valor', ['0'])[0].isdigit() else 0
                    stock = int(fields.get('stock', ['0'])[0]) if fields.get('stock', ['0'])[0].isdigit() else 0
                except ValueError:
                    self.send_response(302)
                    self.send_header("Location", "/agregar_producto?error=Valores+numericos+invalidos")
                    self.end_headers()
                    return

                # Validaciones básicas
                if not all([codigo, nombre, descripcion, imagen]):
                    self.send_response(302)
                    self.send_header("Location", "/agregar_producto?error=Todos+los+campos+son+requeridos")
                    self.end_headers()
                    return

                if valor <= 0:
                    self.send_response(302)
                    self.send_header("Location", "/agregar_producto?error=El+precio+debe+ser+mayor+a+0")
                    self.end_headers()
                    return

                if stock < 0:
                    self.send_response(302)
                    self.send_header("Location", "/agregar_producto?error=El+stock+no+puede+ser+negativo")
                    self.end_headers()
                    return

                # Conectar a base de datos
                conn = sqlite3.connect("ferremas.db")
                cursor = conn.cursor()

                # Verificar si ya existe producto con mismo código
                cursor.execute("SELECT codigo FROM productos WHERE codigo = ?", (codigo,))
                if cursor.fetchone():
                    self.send_response(302)
                    self.send_header("Location", "/agregar_producto?error=Ya+existe+un+producto+con+ese+codigo")
                    self.end_headers()
                    return

                # Insertar nuevo producto
                cursor.execute(
                    "INSERT INTO productos (codigo, nombre, descripcion, stock, valor, imagen) VALUES (?, ?, ?, ?, ?, ?)",
                    (codigo, nombre, descripcion, stock, valor, imagen)
                )
                conn.commit()
                
                # Redireccionar al catálogo con mensaje de éxito
                self.send_response(302)
                self.send_header("Location", f"/catalog?mensaje=Producto+{nombre}+agregado+exitosamente")
                self.end_headers()

            except sqlite3.Error as e:
                print(f"Error de base de datos al agregar producto: {e}")
                self.send_response(302)
                self.send_header("Location", "/agregar_producto?error=Error+de+base+de+datos")
                self.end_headers()
            except Exception as e:
                print(f"Error general al agregar producto: {e}")
                self.send_response(302)
                self.send_header("Location", "/agregar_producto?error=Error+interno+del+servidor")
                self.end_headers()
            finally:
                if 'conn' in locals():
                    conn.close()
            return

# Cambiar el directorio raíz para servir archivos desde el proyecto
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Para poder utilizarlo en otro pc
with socketserver.TCPServer(("0.0.0.0", PORT), MyHandler) as httpd:
    print(f"Servidor corriendo en http://localhost:{PORT}")
    httpd.serve_forever()