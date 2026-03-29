#!/usr/bin/env python3
"""
Programa para cambiar el ID Modbus de sondas de temperatura/humedad.
Puerto: autodetección USB-Serial
Baudrate: 4800, 8N1
Registro de ID: 2000 (0x07D0)
"""

import serial
import serial.tools.list_ports
import struct
import time
import sys


def crc16_modbus(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def send_recv(ser, frame_data, timeout=0.5):
    crc = crc16_modbus(frame_data)
    frame = frame_data + struct.pack('<H', crc)
    ser.reset_input_buffer()
    ser.write(frame)
    time.sleep(timeout)
    return ser.read(100)


def leer_sonda(ser, slave_id):
    """Lee temperatura y humedad de una sonda. Devuelve (temp, hum) o None."""
    resp = send_recv(ser, bytes([slave_id, 0x03, 0x00, 0x00, 0x00, 0x02]))
    if resp and len(resp) >= 9 and resp[0] == slave_id:
        hum = ((resp[3] << 8) | resp[4]) / 10.0
        temp = ((resp[5] << 8) | resp[6]) / 10.0
        return temp, hum
    return None


def cambiar_id(ser, id_actual, id_nuevo):
    """Cambia el ID de la sonda escribiendo en registro 2000 (0x07D0)."""
    resp = send_recv(ser, bytes([
        id_actual, 0x06, 0x07, 0xD0, 0x00, id_nuevo
    ]))
    if resp and len(resp) >= 6 and resp[0] == id_actual:
        return True
    return False


def detectar_puerto():
    """Detecta el puerto USB-Serial automáticamente."""
    puertos = serial.tools.list_ports.comports()
    usb_puertos = [p for p in puertos if 'usb' in p.device.lower()]
    if len(usb_puertos) == 1:
        return usb_puertos[0].device
    elif len(usb_puertos) > 1:
        print("\nPuertos USB detectados:")
        for i, p in enumerate(usb_puertos):
            print(f"  {i + 1}. {p.device} ({p.description})")
        sel = input("Selecciona el número de puerto: ").strip()
        try:
            return usb_puertos[int(sel) - 1].device
        except (ValueError, IndexError):
            return None
    return None


def escanear_sondas(ser, rango=(1, 20)):
    """Escanea un rango de IDs buscando sondas activas."""
    encontradas = []
    print(f"\nEscaneando IDs {rango[0]}-{rango[1]}...", end="", flush=True)
    for slave_id in range(rango[0], rango[1] + 1):
        resultado = leer_sonda(ser, slave_id)
        if resultado:
            encontradas.append((slave_id, resultado[0], resultado[1]))
            print(f"\n  ID {slave_id}: Temp={resultado[0]}°C, Hum={resultado[1]}%", end="", flush=True)
        else:
            print(".", end="", flush=True)
    print()
    return encontradas


def main():
    print("=" * 50)
    print("  CAMBIAR ID DE SONDAS MODBUS")
    print("  Temperatura / Humedad")
    print("=" * 50)

    # Detectar puerto
    puerto = detectar_puerto()
    if not puerto:
        print("\n✗ No se detectó ningún adaptador USB-Serial.")
        print("  Conecta el adaptador USB-Modbus y vuelve a ejecutar.")
        sys.exit(1)

    print(f"\nPuerto detectado: {puerto}")

    # Abrir puerto
    try:
        ser = serial.Serial(
            port=puerto, baudrate=4800, parity='N',
            stopbits=1, bytesize=8, timeout=2
        )
    except serial.SerialException as e:
        print(f"\n✗ Error abriendo puerto: {e}")
        sys.exit(1)

    while True:
        print("\n--- MENÚ ---")
        print("1. Escanear sondas conectadas")
        print("2. Leer sonda por ID")
        print("3. Cambiar ID de una sonda")
        print("4. Salir")

        opcion = input("\nElige opción: ").strip()

        if opcion == "1":
            try:
                rango_max = input("ID máximo a escanear (por defecto 20): ").strip()
                rango_max = int(rango_max) if rango_max else 20
            except ValueError:
                rango_max = 20
            encontradas = escanear_sondas(ser, (1, rango_max))
            if encontradas:
                print(f"\nSondas encontradas: {len(encontradas)}")
                for sid, temp, hum in encontradas:
                    print(f"  ID {sid}: {temp}°C, {hum}%")
            else:
                print("\nNo se encontraron sondas.")

        elif opcion == "2":
            try:
                sid = int(input("ID de la sonda: ").strip())
            except ValueError:
                print("ID no válido.")
                continue
            resultado = leer_sonda(ser, sid)
            if resultado:
                print(f"\n  Temperatura: {resultado[0]}°C")
                print(f"  Humedad:     {resultado[1]}%")
            else:
                print(f"\n  ✗ Sin respuesta de ID {sid}")

        elif opcion == "3":
            try:
                id_actual = int(input("ID actual de la sonda: ").strip())
                id_nuevo = int(input("Nuevo ID (1-247): ").strip())
            except ValueError:
                print("ID no válido.")
                continue

            if not (1 <= id_nuevo <= 247):
                print("El ID debe estar entre 1 y 247.")
                continue

            if id_actual == id_nuevo:
                print("El ID nuevo es igual al actual.")
                continue

            # Verificar que la sonda responde en el ID actual
            print(f"\nVerificando sonda en ID {id_actual}...", end=" ")
            resultado = leer_sonda(ser, id_actual)
            if not resultado:
                print(f"✗ No hay respuesta en ID {id_actual}")
                continue
            print(f"OK ({resultado[0]}°C, {resultado[1]}%)")

            # Cambiar ID
            print(f"Cambiando ID {id_actual} -> {id_nuevo}...", end=" ")
            if cambiar_id(ser, id_actual, id_nuevo):
                time.sleep(1)
                # Verificar con nuevo ID
                resultado_nuevo = leer_sonda(ser, id_nuevo)
                if resultado_nuevo:
                    print(f"✓ ¡Cambiado!")
                    print(f"\n  Verificación con ID {id_nuevo}:")
                    print(f"  Temperatura: {resultado_nuevo[0]}°C")
                    print(f"  Humedad:     {resultado_nuevo[1]}%")
                else:
                    print("⚠ Se envió el comando pero no responde en el nuevo ID.")
                    # Comprobar si sigue en el anterior
                    resultado_old = leer_sonda(ser, id_actual)
                    if resultado_old:
                        print(f"  La sonda sigue respondiendo en ID {id_actual}")
            else:
                print("✗ Error al enviar el comando.")

        elif opcion == "4":
            break
        else:
            print("Opción no válida.")

    ser.close()
    print("\nPrograma finalizado.")


if __name__ == "__main__":
    main()
