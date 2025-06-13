#!/usr/bin/env python3
"""
Script para inicializar la base de datos con las tablas necesarias
"""

import pedido_model

def main():
    print("Inicializando base de datos...")
    
    # Crear las tablas necesarias
    pedido_model.inicializar_base_datos()
    print("✅ Tablas de pedidos creadas correctamente")
    
    # Preguntar si quiere insertar datos de prueba
    respuesta = input("¿Deseas insertar pedidos de prueba? (s/n): ").lower().strip()
    
    if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
        pedido_model.insertar_pedidos_prueba()
        print("✅ Pedidos de prueba insertados")
    
    print("🎉 Inicialización completada!")

if __name__ == "__main__":
    main()