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


def send_recv(ser, frame_data, timeout=0.3):
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
        self.buscando = False
        self.id_encontrado = None

        # Estilo
        style = ttk.Style()
        style.configure("Big.TButton", font=("Arial", 14), padding=10)
        style.configure("Header.TLabel", font=("Arial", 16, "bold"))
        style.configure("Info.TLabel", font=("Arial", 13))
        style.configure("Result.TLabel", font=("Arial", 14, "bold"))
        style.configure("OK.TLabel", font=("Arial", 14, "bold"), foreground="green")
        style.configure("Error.TLabel", font=("Arial", 14, "bold"), foreground="red")
        style.configure("Progress.TLabel", font=("Arial", 12), foreground="#666")

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

        # --- Buscar sonda ---
        frame_buscar = ttk.LabelFrame(main, text=" 1. Buscar sonda conectada ", padding=10)
        frame_buscar.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.btn_buscar = ttk.Button(frame_buscar, text="BUSCAR SONDA", style="Big.TButton",
                                      command=self.buscar_sonda)
        self.btn_buscar.grid(row=0, column=0, columnspan=3, sticky="ew")

        self.lbl_progreso = ttk.Label(frame_buscar, text="", style="Progress.TLabel")
        self.lbl_progreso.grid(row=1, column=0, columnspan=3, pady=(5, 0))

        self.progress = ttk.Progressbar(frame_buscar, length=400, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=3, pady=(5, 0))

        self.lbl_sonda = ttk.Label(frame_buscar, text="", style="Info.TLabel")
        self.lbl_sonda.grid(row=3, column=0, columnspan=3, sticky="w", pady=(5, 0))

        self.lbl_temp = ttk.Label(frame_buscar, text="", style="Info.TLabel")
        self.lbl_temp.grid(row=4, column=0, columnspan=3, sticky="w")

        self.lbl_hum = ttk.Label(frame_buscar, text="", style="Info.TLabel")
        self.lbl_hum.grid(row=5, column=0, columnspan=3, sticky="w")

        # --- Cambiar ID ---
        frame_cambiar = ttk.LabelFrame(main, text=" 2. Cambiar ID ", padding=10)
        frame_cambiar.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame_cambiar, text="Nuevo ID (1-247):", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.spin_id_nuevo = ttk.Spinbox(frame_cambiar, from_=1, to=247, width=5, font=("Arial", 14))
        self.spin_id_nuevo.grid(row=0, column=1, padx=5, sticky="w")
        self.spin_id_nuevo.set(2)

        self.btn_cambiar = ttk.Button(frame_cambiar, text="CAMBIAR ID", style="Big.TButton",
                                       command=self.cambiar)
        self.btn_cambiar.grid(row=0, column=2, padx=5)

        self.lbl_resultado = ttk.Label(frame_cambiar, text="", style="Info.TLabel")
        self.lbl_resultado.grid(row=1, column=0, columnspan=3, pady=(10, 0))

        # Detectar puertos al inicio
        self.actualizar_puertos()

    def actualizar_puertos(self):
        puertos = serial.tools.list_ports.comports()
        encontrados = []
        for p in puertos:
            texto = f"{p.device} {p.description} {p.hwid}".lower()
            if 'usb' in texto or 'serial' in texto or 'ch340' in texto or 'cp210' in texto or 'ftdi' in texto:
                encontrados.append(f"{p.device} - {p.description}")
        self.combo_puerto['values'] = encontrados if encontrados else ["No se detectan puertos"]
        if encontrados:
            self.combo_puerto.current(0)

    def toggle_conexion(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            self.btn_conectar.config(text="Conectar")
            self.lbl_estado.config(text="Desconectado", style="Error.TLabel")
        else:
            puerto = self.combo_puerto.get().split(" - ")[0].strip()
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

    def buscar_sonda(self):
        if not self.check_conexion():
            return
        if self.buscando:
            self.buscando = False
            return

        self.buscando = True
        self.id_encontrado = None
        self.btn_buscar.config(text="PARAR")
        self.lbl_sonda.config(text="")
        self.lbl_temp.config(text="")
        self.lbl_hum.config(text="")
        self.progress['value'] = 0
        self.progress['maximum'] = 247

        def search_thread():
            for sid in range(1, 248):
                if not self.buscando:
                    self.root.after(0, lambda: self.lbl_progreso.config(text="Busqueda cancelada"))
                    break

                self.root.after(0, lambda s=sid: self._update_progress(s))

                resultado = leer_sonda(self.ser, sid)
                if resultado:
                    self.id_encontrado = sid
                    self.root.after(0, lambda s=sid, t=resultado[0], h=resultado[1]: self._sonda_encontrada(s, t, h))
                    break
            else:
                self.root.after(0, self._sonda_no_encontrada)

            self.buscando = False
            self.root.after(0, lambda: self.btn_buscar.config(text="BUSCAR SONDA"))

        threading.Thread(target=search_thread, daemon=True).start()

    def _update_progress(self, sid):
        self.progress['value'] = sid
        self.lbl_progreso.config(text=f"Probando ID {sid} de 247...")

    def _sonda_encontrada(self, sid, temp, hum):
        self.progress['value'] = 247
        self.lbl_progreso.config(text="")
        self.lbl_sonda.config(text=f"Sonda encontrada en ID {sid}", style="OK.TLabel")
        self.lbl_temp.config(text=f"Temperatura:  {temp} °C")
        self.lbl_hum.config(text=f"Humedad:       {hum} %")

    def _sonda_no_encontrada(self):
        self.lbl_progreso.config(text="")
        self.lbl_sonda.config(text="No se encontro ninguna sonda (IDs 1-247)", style="Error.TLabel")
        self.lbl_temp.config(text="")
        self.lbl_hum.config(text="")

    def cambiar(self):
        if not self.check_conexion():
            return

        if not self.id_encontrado:
            messagebox.showwarning("Aviso", "Primero busca la sonda con el boton 'BUSCAR SONDA'.")
            return

        try:
            id_nuevo = int(self.spin_id_nuevo.get())
        except ValueError:
            return

        if self.id_encontrado == id_nuevo:
            messagebox.showinfo("Aviso", "El ID nuevo es igual al actual.")
            return

        if not (1 <= id_nuevo <= 247):
            messagebox.showerror("Error", "El ID debe estar entre 1 y 247.")
            return

        resp = messagebox.askyesno("Confirmar",
            f"¿Cambiar ID de {self.id_encontrado} a {id_nuevo}?")
        if not resp:
            return

        self.lbl_resultado.config(text="Cambiando ID...", style="Info.TLabel")
        self.root.update()

        ok = cambiar_id_sonda(self.ser, self.id_encontrado, id_nuevo)
        if not ok:
            self.lbl_resultado.config(text="Error al enviar comando", style="Error.TLabel")
            return

        time.sleep(1)

        resultado_nuevo = leer_sonda(self.ser, id_nuevo)
        if resultado_nuevo:
            self.lbl_resultado.config(
                text=f"ID cambiado a {id_nuevo}  ({resultado_nuevo[0]}°C, {resultado_nuevo[1]}%)",
                style="OK.TLabel")
            self.id_encontrado = id_nuevo
            self.lbl_sonda.config(text=f"Sonda encontrada en ID {id_nuevo}", style="OK.TLabel")
            messagebox.showinfo("Exito",
                f"ID cambiado correctamente a {id_nuevo}\n\n"
                f"Temperatura: {resultado_nuevo[0]}°C\n"
                f"Humedad: {resultado_nuevo[1]}%")
        else:
            self.lbl_resultado.config(
                text="Comando enviado pero no responde en nuevo ID", style="Error.TLabel")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
