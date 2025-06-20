from model import user_model

def login_controller(params):
    email = params.get("email", [""])[0]
    password = params.get("password", [""])[0]

    if user_model.verificar_usuario(email, password):
        return ("200 OK", "view/catalog.html")
    else:
        return ("401 Unauthorized", "view/login.html")