import http.server
import socketserver
import urllib.parse
import os
import sqlite3

from model import product_model
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
import uuid
from http import cookies

webpay_options = WebpayOptions(
    commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
    api_key=IntegrationApiKeys.WEBPAY,
    integration_type=IntegrationType.TEST
)

PORT = 8000


# Carrito de prueba
carrito = []

# Diccionario en memoria para sesiones
sesiones = {}

class MyHandler(http.server.SimpleHTTPRequestHandler):

    def obtener_datos_sesion(self):
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
                        return {"name": row[0], "rol": row[1]}
                except Exception as e:
                    print("Error al obtener sesión desde DB:", e)
                finally:
                    conn.close()
        return None


    def do_GET(self):
        if self.path == "/":
            self.path = "view/index.html"

        elif self.path.startswith("/login"):
            if self.command == "GET":
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

            elif self.command == "POST":
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length).decode("utf-8")
                data = urllib.parse.parse_qs(post_data)

                email = data.get("email", [""])[0]
                password = data.get("password", [""])[0]

                import sqlite3
                conn = sqlite3.connect("database/ferremas.db")
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM usuarios WHERE email = ? AND password = ?", (email, password))
                user = cursor.fetchone()
                conn.close()

                if user:
                    self.send_response(303)
                    self.send_header("Set-Cookie", f"email={email}; Path=/")  # 👈 COOKIE IMPORTANTE
                    self.send_header("Location", "/catalog")
                    self.end_headers()
                else:
                    self.send_response(303)
                    self.send_header("Location", "/login?error=1")
                    self.end_headers()
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

        elif self.path == "/catalog":
            print("Entré al /catalog")
            with open("view/catalog.html", "r", encoding="utf-8") as file:
                html = file.read()

            # Obtener datos del usuario desde la cookie de sesión
            datos_usuario = self.obtener_datos_sesion()
            print("datos_usuario:", datos_usuario)

            rol_html = ""
            btn_add_product = ""

            if datos_usuario:
                rol = datos_usuario.get("rol", "")
                print("Rol del usuario:", rol)
                rol_html = f"<p>Rol: {rol}</p>"

                if rol in ["administrador", "vendedor"]:
                    btn_add_product = '''
                    <div id="add-product-button">
                        <a href="/agregar_producto">
                            <button>➕ Agregar Nuevo Producto</button>
                        </a>
                    </div>
                    '''
            else:
                print("!No se encontraron datos de sesión. El usuario no está autenticado.¡")

            # Armar HTML de productos
            productos_html = ""
            for producto in product_model.listar_productos():
                ruta_imagen = f"/static/img/{producto['imagen']}"
                productos_html += f"""
                <div class="producto">
                    <img src="{ruta_imagen}" alt="{producto['nombre']}" style="width: 200px; height: auto;">
                    <h3>{producto['nombre']}</h3>
                    <p>${producto['valor']}</p>
                    <a href="/product_detail?codigo={producto['codigo']}">Ver más</a>
                </div>
                """

            # Insertar contenido dinámico
            html = html.replace("{{productos}}", productos_html)
            html = html.replace("{{rol}}", rol_html)
            html = html.replace("{{btn_add_product}}", btn_add_product)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return



        elif self.path.startswith("/product_detail"): 
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            codigo = params.get("codigo", [""])[0]

            producto = product_model.obtener_producto_por_codigo(codigo)

            if producto:
                with open("view/product_detail.html", "r", encoding="utf-8") as file:
                    html = file.read()

           
                producto["imagen"] = f"/static/img/{producto['imagen']}"

           
                for key, value in producto.items():
                    html = html.replace(f"{{{{{key}}}}}", str(value))

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            else:
                self.send_error(404, "Producto no encontrado")
            return



        elif self.path.startswith("/add_to_cart"):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            codigo = params.get("codigo", [""])[0]

            if codigo:
                for item in carrito:
                    if item["codigo"] == codigo:
                        item["cantidad"] += 1
                        break
                else:
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

            productos_html = ""
            total = 0

            if carrito:
                for item in carrito:
                    producto = product_model.obtener_producto_por_codigo(item["codigo"])
                    if producto:
                        subtotal = producto["valor"] * item["cantidad"]
                        total += subtotal
                        productos_html += f"""
                        <tr>
                            <td>{producto['nombre']}</td>
                            <td>
                                {item['cantidad']}
                                <a href="/cart?sumar={item['codigo']}">➕</a>
                                <a href="/cart?restar={item['codigo']}">➖</a>
                            </td>
                            <td>${subtotal}</td>
                            <td><a href="/cart?eliminar={item['codigo']}">❌</a></td>
                        </tr>
                        """
                mensaje = ""
            else:
                mensaje = "<strong>Tu carrito está vacío</strong>"

            html = html.replace("{{productos}}", productos_html)
            html = html.replace("{{total}}", f"${total}")
            html = html.replace("{{mensaje_carrito}}", mensaje)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        elif self.path == "/checkout":
            # Calcular el total del carrito
            total = 0
            for item in carrito:
                producto = product_model.obtener_producto_por_codigo(item["codigo"])
                if producto:
                    subtotal = producto["valor"] * item["cantidad"]
                    total += subtotal

            # Crear una orden de compra única
            buy_order = uuid.uuid4().hex[:26]
            session_id = str(uuid.uuid4())
            return_url = "http://localhost:8000/confirmacion_pago"

            # Crear la transacción
            tx = Transaction(webpay_options)
            response = tx.create(buy_order, session_id, total, return_url)

            # Redirigir al usuario al formulario de pago de Webpay
            self.send_response(302)
            self.send_header("Location", response['url'] + "?token_ws=" + response['token'])
            self.end_headers()
            return
        
        elif self.path.startswith("/confirmacion_pago"):
                parsed_url = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed_url.query)

                tbk_token = query.get('TBK_TOKEN', [None])[0]
                tbk_orden_compra = query.get('TBK_ORDEN_COMPRA', [None])[0]
                tbk_id_sesion = query.get('TBK_ID_SESION', [None])[0]

                # Aquí se puede procesar el resultado

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                if tbk_token is None:
                    mensaje = "<h1>Pago aprovado</h1>"
                else:
                    mensaje = f"<h1>Pago cancelado</h1><p>Orden: {tbk_orden_compra}</p>"

                self.wfile.write(f"""
                    <html><body>
                    {mensaje}
                    <p><a href='/catalog'>Volver al catalogo</a></p>
                    </body></html>
                """.encode("utf-8"))
                return
        
        elif self.path == "/agregar_producto":
            with open("view/agregar_producto.html", "r", encoding="utf-8") as file:
                html = file.read()

            mensaje = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("mensaje", [""])[0]
            html = html.replace("{{mensaje}}", f"<p style='color:green;'>{mensaje}</p>" if mensaje else "")

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
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
                    self.send_header("Set-Cookie", f"email={email}; Path=/")  # ← Guardar la cookie
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


        elif self.path.startswith("/register"):
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

            # Confirmar la transacción
            tx = Transaction(webpay_options)
            result = tx.commit(token)

            # Verificar el resultado de la transacción
            if result['status'] == 'AUTHORIZED':
                carrito.clear()  # Vaciar el carrito
                mensaje = "Pago realizado con éxito. Gracias por su compra."
            else:
                mensaje = "El pago no fue autorizado. Intente nuevamente."

            # Mostrar la confirmación
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>{mensaje}</h1></body></html>".encode("utf-8"))
            return
        
        elif self.path == "/agregar_producto": 
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            fields = urllib.parse.parse_qs(post_data.decode('utf-8'))

            codigo = fields.get('codigo', [''])[0]
            nombre = fields.get('nombre', [''])[0]
            valor = int(fields.get('valor', ['0'])[0])
            descripcion = fields.get('descripcion', [''])[0]
            imagen = fields.get('imagen', [''])[0]
            stock = int(fields.get('stock', ['0'])[0])  # 👈 Agregado

            try:
                conn = sqlite3.connect("ferremas.db")
                cursor = conn.cursor()

                # Verificar si ya existe producto con mismo código
                cursor.execute("SELECT * FROM productos WHERE codigo = ?", (codigo,))
                if cursor.fetchone():
                    self.send_response(302)
                    self.send_header("Location", "/agregar_producto?mensaje=Ya+existe+un+producto+con+ese+codigo.")
                    self.end_headers()
                else:
                    cursor.execute(
                        "INSERT INTO productos (codigo, nombre, descripcion, stock, valor, imagen) VALUES (?, ?, ?, ?, ?, ?)",
                        (codigo, nombre, descripcion, stock, valor, imagen)
                    )
                    conn.commit()

                self.send_response(302)
                self.send_header("Location", "/catalog")
                self.end_headers()


            except Exception as e:
                print("Error al agregar producto:", e)
                self.send_error(500, "Error interno del servidor")
            finally:
                conn.close()


        else:
            self.send_error(501, "Unsupported method (POST)")


# Cambiar el directorio raíz para servir archivos desde el proyecto
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# para poder utilizarlo en otro pc
with socketserver.TCPServer(("0.0.0.0", PORT), MyHandler) as httpd:
    print(f"Servidor corriendo en http://localhost:{PORT}")
    httpd.serve_forever()
