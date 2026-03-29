#!/usr/bin/env python3
"""
Configurador de Sondas Aviot
Herramienta para cambiar ID de sondas Modbus de temperatura/humedad.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import struct
import time
import threading
import sys
import os


def resource_path(relative_path):
    """Ruta a recursos empaquetados con PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


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


# Colores corporativos Aviot
AVIOT_NARANJA = "#f39200"
AVIOT_NARANJA_HOVER = "#e08500"
AVIOT_OSCURO = "#1d1d1b"
AVIOT_BLANCO = "#ffffff"
AVIOT_GRIS_CLARO = "#f5f5f5"
AVIOT_GRIS = "#e0e0e0"
AVIOT_VERDE = "#4CAF50"
AVIOT_ROJO = "#e53935"


def show_splash(root):
    """Muestra splash screen de inicio con logo Aviot e instrucciones."""
    splash = tk.Toplevel(root)
    splash.configure(bg=AVIOT_BLANCO)
    splash.title("Configurador de Sondas - Aviot")

    # Centrar en pantalla
    w, h = 700, 720
    x = (splash.winfo_screenwidth() - w) // 2
    y = max(20, (splash.winfo_screenheight() - h) // 2)
    splash.geometry(f"{w}x{h}+{x}+{y}")
    splash.minsize(w, h)

    # Borde naranja
    border = tk.Frame(splash, bg=AVIOT_NARANJA, padx=3, pady=3)
    border.pack(fill="both", expand=True)
    inner = tk.Frame(border, bg=AVIOT_BLANCO)
    inner.pack(fill="both", expand=True)

    # Logo
    try:
        logo_path = resource_path("logo_aviot.png")
        splash.logo_img = tk.PhotoImage(file=logo_path)
        scale_x = max(1, splash.logo_img.width() // 200)
        scale_y = max(1, splash.logo_img.height() // 60)
        scale = max(scale_x, scale_y)
        splash.logo_small = splash.logo_img.subsample(scale, scale)
        tk.Label(inner, image=splash.logo_small, bg=AVIOT_BLANCO).pack(pady=(20, 5))
    except Exception:
        pass

    # Titulo
    tk.Label(inner, text="CONFIGURADOR DE SONDAS",
             font=("Arial", 24, "bold"), fg=AVIOT_NARANJA, bg=AVIOT_BLANCO).pack(pady=(5, 2))

    tk.Label(inner, text="Temperatura y Humedad  |  Modbus RTU  |  v3.4",
             font=("Arial", 12), fg="#888", bg=AVIOT_BLANCO).pack(pady=(0, 5))

    # Linea naranja
    tk.Frame(inner, height=3, bg=AVIOT_NARANJA).pack(fill="x", padx=30, pady=8)

    # Que es este programa
    tk.Label(inner, text="¿Que hace este programa?",
             font=("Arial", 14, "bold"), fg=AVIOT_OSCURO, bg=AVIOT_BLANCO,
             anchor="w").pack(fill="x", padx=30)

    desc = (
        "Este programa permite configurar las sondas de temperatura\n"
        "y humedad que se conectan por Modbus RTU al bus RS485.\n"
        "Detecta automaticamente la sonda conectada y permite\n"
        "cambiar su direccion (ID) para instalarla en el sistema."
    )
    tk.Label(inner, text=desc, font=("Arial", 12), fg="#555", bg=AVIOT_BLANCO,
             justify="left", anchor="w").pack(fill="x", padx=30, pady=(2, 8))

    # Linea gris
    tk.Frame(inner, height=1, bg=AVIOT_GRIS).pack(fill="x", padx=30, pady=3)

    # Como conectar
    tk.Label(inner, text="¿Como conectar la sonda?",
             font=("Arial", 14, "bold"), fg=AVIOT_OSCURO, bg=AVIOT_BLANCO,
             anchor="w").pack(fill="x", padx=30, pady=(5, 0))

    pasos_conexion = (
        "1. Conecta el adaptador USB-Modbus al portatil\n"
        "2. Conecta UNA sola sonda al adaptador:\n"
        "     - Cable A+ (dato positivo)\n"
        "     - Cable B- (dato negativo)\n"
        "     - Alimentacion 12-24V DC a la sonda"
    )
    tk.Label(inner, text=pasos_conexion, font=("Arial", 12), fg="#555",
             bg=AVIOT_BLANCO, justify="left", anchor="w").pack(fill="x", padx=30, pady=(2, 8))

    # Linea gris
    tk.Frame(inner, height=1, bg=AVIOT_GRIS).pack(fill="x", padx=30, pady=3)

    # Driver
    tk.Label(inner, text="Instalacion del driver USB (CH340)",
             font=("Arial", 14, "bold"), fg=AVIOT_OSCURO, bg=AVIOT_BLANCO,
             anchor="w").pack(fill="x", padx=30, pady=(5, 0))

    driver_text = (
        "Si se ha abierto la ventana del instalador del driver,\n"
        "sigue estos pasos para completarlo:\n\n"
        "  1. En la ventana del driver CH340, pulsa 'INSTALL'\n"
        "  2. Espera a que diga 'Driver install success'\n"
        "  3. Pulsa 'OK' y cierra la ventana del driver\n"
        "  4. Conecta el adaptador USB-Modbus al portatil\n"
        "  5. Vuelve aqui y pulsa COMENZAR\n\n"
        "Si no se ha abierto el instalador del driver, es que ya\n"
        "lo tienes instalado. Pulsa COMENZAR directamente."
    )
    tk.Label(inner, text=driver_text, font=("Arial", 12), fg="#555",
             bg=AVIOT_BLANCO, justify="left", anchor="w").pack(fill="x", padx=30, pady=(2, 5))


    # Linea naranja inferior
    tk.Frame(inner, height=3, bg=AVIOT_NARANJA).pack(fill="x", padx=30, pady=(5, 10))

    # Boton COMENZAR
    def comenzar():
        splash.destroy()
        root.deiconify()

    btn_comenzar = tk.Button(inner, text="COMENZAR", font=("Arial", 18, "bold"),
                             bg=AVIOT_NARANJA, fg=AVIOT_BLANCO,
                             activebackground=AVIOT_NARANJA_HOVER, activeforeground=AVIOT_BLANCO,
                             relief="flat", padx=40, pady=10, cursor="hand2",
                             command=comenzar)
    btn_comenzar.pack(pady=(0, 10))

    # Footer
    tk.Label(inner, text="Aviot - Always Safe  |  Ingeniatic Desarrollo S.L.",
             font=("Arial", 8), fg="#ccc", bg=AVIOT_BLANCO).pack(pady=(0, 8))

    splash.lift()
    splash.focus_force()

    # Icono
    try:
        logo_path = resource_path("logo_aviot.png")
        splash.iconphoto(True, tk.PhotoImage(file=logo_path))
    except Exception:
        pass

    # Cerrar splash con X tambien abre la app
    splash.protocol("WM_DELETE_WINDOW", comenzar)

    root.withdraw()
    return splash


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Configurador de Sondas - Aviot")
        self.root.resizable(False, False)
        self.root.configure(bg=AVIOT_BLANCO)
        self.ser = None
        self.buscando = False
        self.id_encontrado = None

        # Icono
        try:
            logo_path = resource_path("logo_aviot.png")
            self.logo_img = tk.PhotoImage(file=logo_path)
            self.root.iconphoto(True, self.logo_img)
        except Exception:
            self.logo_img = None

        # Estilo corporativo Aviot
        style = ttk.Style()
        style.theme_use('clam')

        style.configure(".", background=AVIOT_BLANCO, foreground=AVIOT_OSCURO)
        style.configure("TFrame", background=AVIOT_BLANCO)
        style.configure("TLabelframe", background=AVIOT_BLANCO, foreground=AVIOT_OSCURO,
                        font=("Arial", 11, "bold"))
        style.configure("TLabelframe.Label", background=AVIOT_BLANCO, foreground=AVIOT_NARANJA,
                        font=("Arial", 11, "bold"))

        style.configure("Aviot.TButton",
                        font=("Arial", 13, "bold"),
                        padding=10,
                        background=AVIOT_NARANJA,
                        foreground=AVIOT_BLANCO)
        style.map("Aviot.TButton",
                  background=[('active', AVIOT_NARANJA_HOVER), ('pressed', AVIOT_OSCURO)])

        style.configure("Header.TLabel", font=("Arial", 18, "bold"),
                        foreground=AVIOT_NARANJA, background=AVIOT_BLANCO)
        style.configure("Sub.TLabel", font=("Arial", 10),
                        foreground="#888", background=AVIOT_BLANCO)
        style.configure("Info.TLabel", font=("Arial", 13),
                        foreground=AVIOT_OSCURO, background=AVIOT_BLANCO)
        style.configure("OK.TLabel", font=("Arial", 14, "bold"),
                        foreground=AVIOT_VERDE, background=AVIOT_BLANCO)
        style.configure("Error.TLabel", font=("Arial", 14, "bold"),
                        foreground=AVIOT_ROJO, background=AVIOT_BLANCO)
        style.configure("Progress.TLabel", font=("Arial", 11),
                        foreground="#888", background=AVIOT_BLANCO)
        style.configure("Link.TLabel", font=("Arial", 10, "underline"),
                        foreground="#1a73e8", background=AVIOT_BLANCO, cursor="hand2")

        style.configure("Aviot.Horizontal.TProgressbar",
                        troughcolor=AVIOT_GRIS,
                        background=AVIOT_NARANJA,
                        thickness=20)

        main = ttk.Frame(root, padding=20)
        main.grid(sticky="nsew")

        # Logo + Titulo
        frame_header = ttk.Frame(main)
        frame_header.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        if self.logo_img:
            try:
                small_logo = self.logo_img.subsample(
                    max(1, self.logo_img.width() // 180),
                    max(1, self.logo_img.height() // 50)
                )
                self.small_logo = small_logo
                ttk.Label(frame_header, image=self.small_logo, background=AVIOT_BLANCO).grid(
                    row=0, column=0, pady=(0, 5))
            except Exception:
                pass

        ttk.Label(frame_header, text="CONFIGURADOR DE SONDAS", style="Header.TLabel").grid(
            row=1, column=0)
        ttk.Label(frame_header, text="Temperatura y Humedad  |  Modbus RTU", style="Sub.TLabel").grid(
            row=2, column=0)

        # Linea separadora naranja
        sep = tk.Frame(main, height=3, bg=AVIOT_NARANJA)
        sep.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        # --- Conexion ---
        frame_con = ttk.LabelFrame(main, text=" Conexion ", padding=10)
        frame_con.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame_con, text="Puerto:", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.combo_puerto = ttk.Combobox(frame_con, width=30, font=("Arial", 12), state="readonly")
        self.combo_puerto.grid(row=0, column=1, padx=5)
        ttk.Button(frame_con, text="Actualizar", command=self.actualizar_puertos).grid(row=0, column=2, padx=5)

        self.btn_conectar = ttk.Button(frame_con, text="Conectar", style="Aviot.TButton",
                                        command=self.toggle_conexion)
        self.btn_conectar.grid(row=1, column=0, columnspan=3, pady=(10, 0), sticky="ew")

        self.lbl_estado = ttk.Label(frame_con, text="Desconectado", style="Error.TLabel")
        self.lbl_estado.grid(row=2, column=0, columnspan=3, pady=(5, 0))

        # --- Buscar sonda ---
        frame_buscar = ttk.LabelFrame(main, text=" 1. Buscar sonda conectada ", padding=10)
        frame_buscar.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.btn_buscar = ttk.Button(frame_buscar, text="BUSCAR SONDA", style="Aviot.TButton",
                                      command=self.buscar_sonda)
        self.btn_buscar.grid(row=0, column=0, columnspan=3, sticky="ew")

        self.lbl_progreso = ttk.Label(frame_buscar, text="", style="Progress.TLabel")
        self.lbl_progreso.grid(row=1, column=0, columnspan=3, pady=(5, 0))

        self.progress = ttk.Progressbar(frame_buscar, length=400, mode='determinate',
                                         style="Aviot.Horizontal.TProgressbar")
        self.progress.grid(row=2, column=0, columnspan=3, pady=(5, 0))

        self.lbl_sonda = ttk.Label(frame_buscar, text="", style="Info.TLabel")
        self.lbl_sonda.grid(row=3, column=0, columnspan=3, sticky="w", pady=(5, 0))

        self.lbl_temp = ttk.Label(frame_buscar, text="", style="Info.TLabel")
        self.lbl_temp.grid(row=4, column=0, columnspan=3, sticky="w")

        self.lbl_hum = ttk.Label(frame_buscar, text="", style="Info.TLabel")
        self.lbl_hum.grid(row=5, column=0, columnspan=3, sticky="w")

        # --- Cambiar ID ---
        frame_cambiar = ttk.LabelFrame(main, text=" 2. Cambiar ID ", padding=10)
        frame_cambiar.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame_cambiar, text="Nuevo ID (1-247):", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.spin_id_nuevo = ttk.Spinbox(frame_cambiar, from_=1, to=247, width=5, font=("Arial", 14))
        self.spin_id_nuevo.grid(row=0, column=1, padx=5, sticky="w")
        self.spin_id_nuevo.set(2)

        self.btn_cambiar = ttk.Button(frame_cambiar, text="CAMBIAR ID", style="Aviot.TButton",
                                       command=self.cambiar)
        self.btn_cambiar.grid(row=0, column=2, padx=5)

        self.lbl_resultado = ttk.Label(frame_cambiar, text="", style="Info.TLabel")
        self.lbl_resultado.grid(row=1, column=0, columnspan=3, pady=(10, 0))

        # --- Ayuda ---
        frame_ayuda = ttk.LabelFrame(main, text=" Ayuda ", padding=10)
        frame_ayuda.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ayuda_text = (
            "1. Conecta el adaptador USB-Modbus al portatil\n"
            "2. Conecta UNA sola sonda (cables A+, B- y alimentacion 12-24V)\n"
            "3. Pulsa 'Conectar' para abrir el puerto serie\n"
            "4. Pulsa 'BUSCAR SONDA' para detectar el ID actual\n"
            "5. Introduce el nuevo ID y pulsa 'CAMBIAR ID'\n"
            "\n"
            "Si no detecta el puerto, reinstala el driver desde\n"
            "la carpeta de instalacion (drivers/CH341SER.EXE)."
        )
        lbl_ayuda = ttk.Label(frame_ayuda, text=ayuda_text,
                              wraplength=450, justify="left", font=("Arial", 10))
        lbl_ayuda.grid(row=0, column=0, columnspan=3, sticky="w")

        # --- Footer ---
        footer = ttk.Label(main, text="Aviot - Always Safe  |  aviot.es  |  Ingeniatic Desarrollo S.L.",
                          font=("Arial", 9), foreground="#aaa", background=AVIOT_BLANCO)
        footer.grid(row=6, column=0, columnspan=3, pady=(5, 0))

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

    # Configurar estilo antes del splash
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Aviot.Horizontal.TProgressbar",
                    troughcolor=AVIOT_GRIS, background=AVIOT_NARANJA, thickness=20)

    app_holder = {}

    def on_splash_close():
        if not app_holder:
            app_holder['app'] = App(root)

    splash = show_splash(root)
    # La App se crea cuando el usuario pulsa COMENZAR (via splash.destroy -> root.deiconify)
    root.bind("<Map>", lambda e: on_splash_close())
    root.mainloop()
