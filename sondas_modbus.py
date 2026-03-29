#!/usr/bin/env python3
"""
Sondas Modbus - Herramienta para cambiar ID de sondas de temperatura/humedad.
Interfaz gráfica sencilla para uso en campo.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import struct
import time
import threading


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
    resp = send_recv(ser, bytes([slave_id, 0x03, 0x00, 0x00, 0x00, 0x02]))
    if resp and len(resp) >= 9 and resp[0] == slave_id:
        hum = ((resp[3] << 8) | resp[4]) / 10.0
        temp = ((resp[5] << 8) | resp[6]) / 10.0
        return temp, hum
    return None


def cambiar_id_sonda(ser, id_actual, id_nuevo):
    resp = send_recv(ser, bytes([id_actual, 0x06, 0x07, 0xD0, 0x00, id_nuevo]))
    if resp and len(resp) >= 6 and resp[0] == id_actual:
        return True
    return False


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Sondas Modbus - Cambiar ID")
        self.root.resizable(False, False)
        self.ser = None

        # Estilo
        style = ttk.Style()
        style.configure("Big.TButton", font=("Arial", 14), padding=10)
        style.configure("Header.TLabel", font=("Arial", 16, "bold"))
        style.configure("Info.TLabel", font=("Arial", 13))
        style.configure("Result.TLabel", font=("Arial", 14, "bold"))
        style.configure("OK.TLabel", font=("Arial", 14, "bold"), foreground="green")
        style.configure("Error.TLabel", font=("Arial", 14, "bold"), foreground="red")

        main = ttk.Frame(root, padding=20)
        main.grid(sticky="nsew")

        # Titulo
        ttk.Label(main, text="SONDAS MODBUS", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, pady=(0, 15))

        # --- Conexion ---
        frame_con = ttk.LabelFrame(main, text=" Conexion ", padding=10)
        frame_con.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame_con, text="Puerto:", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.combo_puerto = ttk.Combobox(frame_con, width=30, font=("Arial", 12), state="readonly")
        self.combo_puerto.grid(row=0, column=1, padx=5)
        ttk.Button(frame_con, text="Actualizar", command=self.actualizar_puertos).grid(row=0, column=2, padx=5)

        self.btn_conectar = ttk.Button(frame_con, text="Conectar", style="Big.TButton",
                                        command=self.toggle_conexion)
        self.btn_conectar.grid(row=1, column=0, columnspan=3, pady=(10, 0), sticky="ew")

        self.lbl_estado = ttk.Label(frame_con, text="Desconectado", style="Error.TLabel")
        self.lbl_estado.grid(row=2, column=0, columnspan=3, pady=(5, 0))

        # --- Leer sonda ---
        frame_leer = ttk.LabelFrame(main, text=" Leer sonda ", padding=10)
        frame_leer.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame_leer, text="ID de la sonda:", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.spin_id_leer = ttk.Spinbox(frame_leer, from_=1, to=247, width=5, font=("Arial", 14))
        self.spin_id_leer.grid(row=0, column=1, padx=5)
        self.spin_id_leer.set(1)

        ttk.Button(frame_leer, text="Leer", style="Big.TButton",
                   command=self.leer).grid(row=0, column=2, padx=5)

        self.lbl_temp = ttk.Label(frame_leer, text="Temperatura: --", style="Info.TLabel")
        self.lbl_temp.grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self.lbl_hum = ttk.Label(frame_leer, text="Humedad: --", style="Info.TLabel")
        self.lbl_hum.grid(row=2, column=0, columnspan=3, sticky="w")

        # --- Cambiar ID ---
        frame_cambiar = ttk.LabelFrame(main, text=" Cambiar ID ", padding=10)
        frame_cambiar.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame_cambiar, text="ID actual:", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.spin_id_actual = ttk.Spinbox(frame_cambiar, from_=1, to=247, width=5, font=("Arial", 14))
        self.spin_id_actual.grid(row=0, column=1, padx=5, sticky="w")
        self.spin_id_actual.set(1)

        ttk.Label(frame_cambiar, text="Nuevo ID:", font=("Arial", 12)).grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.spin_id_nuevo = ttk.Spinbox(frame_cambiar, from_=1, to=247, width=5, font=("Arial", 14))
        self.spin_id_nuevo.grid(row=1, column=1, padx=5, sticky="w", pady=(5, 0))
        self.spin_id_nuevo.set(2)

        ttk.Button(frame_cambiar, text="CAMBIAR ID", style="Big.TButton",
                   command=self.cambiar).grid(row=0, column=2, rowspan=2, padx=5, sticky="ns")

        self.lbl_resultado = ttk.Label(frame_cambiar, text="", style="Info.TLabel")
        self.lbl_resultado.grid(row=2, column=0, columnspan=3, pady=(10, 0))

        # --- Escanear ---
        frame_scan = ttk.LabelFrame(main, text=" Escanear bus ", padding=10)
        frame_scan.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame_scan, text="Escanear IDs del 1 al:", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.spin_scan_max = ttk.Spinbox(frame_scan, from_=1, to=247, width=5, font=("Arial", 14))
        self.spin_scan_max.grid(row=0, column=1, padx=5)
        self.spin_scan_max.set(20)

        ttk.Button(frame_scan, text="Escanear", style="Big.TButton",
                   command=self.escanear).grid(row=0, column=2, padx=5)

        self.txt_scan = tk.Text(frame_scan, height=5, width=45, font=("Arial", 12), state="disabled")
        self.txt_scan.grid(row=1, column=0, columnspan=3, pady=(10, 0))

        # Detectar puertos al inicio
        self.actualizar_puertos()

    def actualizar_puertos(self):
        puertos = serial.tools.list_ports.comports()
        usb = [p.device for p in puertos if 'usb' in p.device.lower()]
        self.combo_puerto['values'] = usb if usb else ["No se detectan puertos"]
        if usb:
            self.combo_puerto.current(0)

    def toggle_conexion(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            self.btn_conectar.config(text="Conectar")
            self.lbl_estado.config(text="Desconectado", style="Error.TLabel")
        else:
            puerto = self.combo_puerto.get()
            if not puerto or "No se detectan" in puerto:
                messagebox.showerror("Error", "Conecta el adaptador USB-Modbus y pulsa Actualizar.")
                return
            try:
                self.ser = serial.Serial(
                    port=puerto, baudrate=4800, parity='N',
                    stopbits=1, bytesize=8, timeout=2
                )
                self.btn_conectar.config(text="Desconectar")
                self.lbl_estado.config(text=f"Conectado a {puerto}", style="OK.TLabel")
            except serial.SerialException as e:
                messagebox.showerror("Error", f"No se pudo abrir el puerto:\n{e}")

    def check_conexion(self):
        if not self.ser or not self.ser.is_open:
            messagebox.showwarning("Aviso", "Primero conecta el adaptador USB-Modbus.")
            return False
        return True

    def leer(self):
        if not self.check_conexion():
            return
        try:
            sid = int(self.spin_id_leer.get())
        except ValueError:
            return

        self.lbl_temp.config(text="Leyendo...")
        self.lbl_hum.config(text="")
        self.root.update()

        resultado = leer_sonda(self.ser, sid)
        if resultado:
            self.lbl_temp.config(text=f"Temperatura:  {resultado[0]} °C")
            self.lbl_hum.config(text=f"Humedad:       {resultado[1]} %")
        else:
            self.lbl_temp.config(text=f"Sin respuesta de ID {sid}")
            self.lbl_hum.config(text="Comprueba conexion y ID")

    def cambiar(self):
        if not self.check_conexion():
            return
        try:
            id_actual = int(self.spin_id_actual.get())
            id_nuevo = int(self.spin_id_nuevo.get())
        except ValueError:
            return

        if id_actual == id_nuevo:
            messagebox.showinfo("Aviso", "El ID nuevo es igual al actual.")
            return

        if not (1 <= id_nuevo <= 247):
            messagebox.showerror("Error", "El ID debe estar entre 1 y 247.")
            return

        # Confirmar
        resp = messagebox.askyesno("Confirmar",
            f"¿Cambiar ID de {id_actual} a {id_nuevo}?")
        if not resp:
            return

        self.lbl_resultado.config(text="Verificando sonda...", style="Info.TLabel")
        self.root.update()

        # Verificar que existe
        resultado = leer_sonda(self.ser, id_actual)
        if not resultado:
            self.lbl_resultado.config(text=f"No hay respuesta en ID {id_actual}", style="Error.TLabel")
            return

        self.lbl_resultado.config(text="Cambiando ID...", style="Info.TLabel")
        self.root.update()

        # Cambiar
        ok = cambiar_id_sonda(self.ser, id_actual, id_nuevo)
        if not ok:
            self.lbl_resultado.config(text="Error al enviar comando", style="Error.TLabel")
            return

        time.sleep(1)

        # Verificar nuevo ID
        resultado_nuevo = leer_sonda(self.ser, id_nuevo)
        if resultado_nuevo:
            self.lbl_resultado.config(
                text=f"ID cambiado a {id_nuevo}  ({resultado_nuevo[0]}°C, {resultado_nuevo[1]}%)",
                style="OK.TLabel")
            messagebox.showinfo("Exito",
                f"ID cambiado correctamente de {id_actual} a {id_nuevo}\n\n"
                f"Temperatura: {resultado_nuevo[0]}°C\n"
                f"Humedad: {resultado_nuevo[1]}%")
        else:
            self.lbl_resultado.config(
                text="Comando enviado pero no responde en nuevo ID", style="Error.TLabel")

    def escanear(self):
        if not self.check_conexion():
            return
        try:
            max_id = int(self.spin_scan_max.get())
        except ValueError:
            return

        self.txt_scan.config(state="normal")
        self.txt_scan.delete("1.0", tk.END)
        self.txt_scan.insert(tk.END, "Escaneando...\n")
        self.txt_scan.config(state="disabled")
        self.root.update()

        def scan_thread():
            encontradas = []
            for sid in range(1, max_id + 1):
                resultado = leer_sonda(self.ser, sid)
                if resultado:
                    encontradas.append((sid, resultado[0], resultado[1]))
                    self.root.after(0, lambda s=sid, t=resultado[0], h=resultado[1]:
                        self._add_scan_result(f"  ID {s}: {t}°C, {h}%\n"))

            def done():
                self.txt_scan.config(state="normal")
                if not encontradas:
                    self.txt_scan.delete("1.0", tk.END)
                    self.txt_scan.insert(tk.END, "No se encontraron sondas.\n")
                else:
                    self.txt_scan.insert(tk.END, f"\nTotal: {len(encontradas)} sonda(s)\n")
                self.txt_scan.config(state="disabled")

            self.root.after(0, done)

        threading.Thread(target=scan_thread, daemon=True).start()

    def _add_scan_result(self, text):
        self.txt_scan.config(state="normal")
        if self.txt_scan.get("1.0", "1.end") == "Escaneando...":
            self.txt_scan.delete("1.0", "1.end+1c")
        self.txt_scan.insert(tk.END, text)
        self.txt_scan.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
