#!/usr/bin/env python3
"""
Configurador de Sondas Aviot - EDICION DIAGNOSTICO
Version del configurador con logging detallado y diagnostico de sondas.

Anade sobre la version normal:
  - Panel de log en pantalla (trama TX/RX en hexadecimal, valores crudos).
  - Registro automatico a fichero (carpeta Aviot_Sondas_Logs en el perfil del usuario).
  - Validacion de CRC de la respuesta y deteccion de excepciones Modbus.
  - Lectura repetida (varias muestras) para distinguir sonda averiada de fallo puntual.
  - Boton DIAGNOSTICO que da un veredicto claro al usuario:
      * No responde            -> problema de cableado / alimentacion / bus.
      * Comunica pero 0.0/0.0   -> el sensor interno esta averiado.
      * Lecturas validas        -> sonda correcta.
  - Botones para abrir la carpeta de logs y copiar el log (para enviarlo a soporte).
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import struct
import time
import threading
import sys
import os
import platform
import subprocess

VERSION = "v3.6-DIAG"


# ---------------------------------------------------------------------------
#  Utilidades de rutas / ficheros
# ---------------------------------------------------------------------------
def resource_path(relative_path):
    """Ruta a recursos empaquetados con PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def logs_dir():
    """Carpeta de logs en el perfil del usuario (siempre con permiso de escritura)."""
    carpeta = os.path.join(os.path.expanduser("~"), "Aviot_Sondas_Logs")
    try:
        os.makedirs(carpeta, exist_ok=True)
    except Exception:
        carpeta = os.path.expanduser("~")
    return carpeta


# ---------------------------------------------------------------------------
#  Comunicaciones Modbus (instrumentadas con log)
# ---------------------------------------------------------------------------
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


def build_frame(frame_data):
    crc = crc16_modbus(frame_data)
    return frame_data + struct.pack('<H', crc)


def fmt_hex(b):
    if not b:
        return "(vacio)"
    return " ".join(f"{x:02X}" for x in b)


def transaccion(ser, frame_data, timeout=0.3, log=None, verbose=True):
    """Envia una trama Modbus y devuelve la respuesta cruda. Registra TX/RX si verbose."""
    frame = build_frame(frame_data)
    ser.reset_input_buffer()
    ser.write(frame)
    time.sleep(timeout)
    resp = ser.read(100)
    if log and verbose:
        log(f"   TX -> {fmt_hex(frame)}")
        log(f"   RX <- {fmt_hex(resp)}")
    return resp


def leer_sonda_detallado(ser, slave_id, log=None, verbose=True):
    """
    Lee Tª/HR (FC03, registros 0x0000-0x0001) y devuelve un diccionario con todo
    el detalle: bytes crudos, valores de registro, CRC, errores, etc.
    """
    res = {
        'slave_id': slave_id, 'ok': False,
        'temp': None, 'hum': None,
        'raw_temp': None, 'raw_hum': None,
        'crc_ok': None, 'error': None, 'resp': b'',
    }
    frame_data = bytes([slave_id, 0x03, 0x00, 0x00, 0x00, 0x02])
    resp = transaccion(ser, frame_data, log=log, verbose=verbose)
    res['resp'] = resp

    if not resp:
        res['error'] = "Sin respuesta (timeout)"
        return res
    if len(resp) < 3:
        res['error'] = f"Respuesta demasiado corta ({len(resp)} bytes)"
        return res
    if resp[0] != slave_id:
        res['error'] = f"ID no coincide (esperado {slave_id}, recibido {resp[0]})"
        return res
    # Excepcion Modbus (bit alto del codigo de funcion)
    if resp[1] & 0x80:
        cod = resp[2] if len(resp) > 2 else 0
        res['error'] = f"Excepcion Modbus (codigo {cod})"
        return res
    if resp[1] != 0x03:
        res['error'] = f"Funcion inesperada (0x{resp[1]:02X})"
        return res
    if len(resp) < 9:
        res['error'] = f"Trama incompleta ({len(resp)} bytes, se esperaban 9)"
        return res

    # Validacion CRC
    datos = resp[:7]
    crc_recibido = resp[7] | (resp[8] << 8)
    crc_calc = crc16_modbus(datos)
    res['crc_ok'] = (crc_recibido == crc_calc)

    raw_hum = (resp[3] << 8) | resp[4]
    raw_temp = (resp[5] << 8) | resp[6]
    res['raw_hum'] = raw_hum
    res['raw_temp'] = raw_temp
    res['hum'] = raw_hum / 10.0
    # Temperatura puede ser negativa (entero con signo de 16 bits)
    res['temp'] = (raw_temp - 65536 if raw_temp > 32767 else raw_temp) / 10.0
    res['ok'] = True
    return res


def leer_sonda(ser, slave_id, log=None, verbose=False):
    """Compatibilidad: devuelve (temp, hum) o None."""
    r = leer_sonda_detallado(ser, slave_id, log=log, verbose=verbose)
    if r['ok']:
        return r['temp'], r['hum']
    return None


def cambiar_id_sonda(ser, id_actual, id_nuevo, log=None):
    """Cambia el ID escribiendo en el registro 0x07D0 (2000). FC06."""
    frame_data = bytes([id_actual, 0x06, 0x07, 0xD0, 0x00, id_nuevo])
    resp = transaccion(ser, frame_data, log=log, verbose=True)
    if resp and len(resp) >= 6 and resp[0] == id_actual and not (resp[1] & 0x80):
        return True
    return False


def volcado_registros(ser, slave_id, cantidad=8, log=None):
    """Lee 'cantidad' registros desde 0x0000 para mostrar el mapa crudo (informativo)."""
    frame_data = bytes([slave_id, 0x03, 0x00, 0x00, 0x00, cantidad])
    resp = transaccion(ser, frame_data, log=log, verbose=True)
    regs = []
    if resp and len(resp) >= 3 + cantidad * 2 and resp[0] == slave_id and resp[1] == 0x03:
        nbytes = resp[2]
        for i in range(0, min(nbytes, cantidad * 2), 2):
            regs.append((resp[3 + i] << 8) | resp[3 + i + 1])
    return regs


# ---------------------------------------------------------------------------
#  Colores corporativos Aviot
# ---------------------------------------------------------------------------
AVIOT_NARANJA = "#f39200"
AVIOT_NARANJA_HOVER = "#e08500"
AVIOT_OSCURO = "#1d1d1b"
AVIOT_BLANCO = "#ffffff"
AVIOT_GRIS_CLARO = "#f5f5f5"
AVIOT_GRIS = "#e0e0e0"
AVIOT_VERDE = "#4CAF50"
AVIOT_ROJO = "#e53935"
AVIOT_AMBAR = "#f9a825"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Configurador de Sondas - Aviot  ({VERSION})")
        self.root.configure(bg=AVIOT_BLANCO)
        self.root.minsize(660, 760)
        self.ser = None
        self.buscando = False
        self.ocupado = False
        self.id_encontrado = None

        # --- Fichero de log ---
        self._log_lock = threading.Lock()
        self.log_path = os.path.join(
            logs_dir(), f"diagnostico_{time.strftime('%Y%m%d_%H%M%S')}.log")
        try:
            self._log_file = open(self.log_path, "a", encoding="utf-8")
        except Exception:
            self._log_file = None

        # Icono
        try:
            logo_path = resource_path("logo_aviot.png")
            self.logo_img = tk.PhotoImage(file=logo_path)
            self.root.iconphoto(True, self.logo_img)
        except Exception:
            self.logo_img = None

        self._build_styles()
        self._build_ui()

        # Cabecera del log
        self.log("=" * 60)
        self.log(f"Configurador de Sondas Aviot {VERSION}")
        self.log(f"Sistema: {platform.platform()}")
        self.log(f"Fecha:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Log:     {self.log_path}")
        self.log("=" * 60)

        self.actualizar_puertos()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----------------------------- estilo -----------------------------
    def _build_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(".", background=AVIOT_BLANCO, foreground=AVIOT_OSCURO)
        style.configure("TFrame", background=AVIOT_BLANCO)
        style.configure("TLabelframe", background=AVIOT_BLANCO, foreground=AVIOT_OSCURO,
                        font=("Arial", 11, "bold"))
        style.configure("TLabelframe.Label", background=AVIOT_BLANCO, foreground=AVIOT_NARANJA,
                        font=("Arial", 11, "bold"))
        style.configure("Aviot.TButton", font=("Arial", 13, "bold"), padding=10,
                        background=AVIOT_NARANJA, foreground=AVIOT_BLANCO)
        style.map("Aviot.TButton",
                  background=[('active', AVIOT_NARANJA_HOVER), ('pressed', AVIOT_OSCURO)])
        style.configure("Diag.TButton", font=("Arial", 13, "bold"), padding=10,
                        background=AVIOT_OSCURO, foreground=AVIOT_BLANCO)
        style.map("Diag.TButton", background=[('active', "#333"), ('pressed', AVIOT_NARANJA)])
        style.configure("Header.TLabel", font=("Arial", 18, "bold"),
                        foreground=AVIOT_NARANJA, background=AVIOT_BLANCO)
        style.configure("Sub.TLabel", font=("Arial", 10), foreground="#888", background=AVIOT_BLANCO)
        style.configure("Info.TLabel", font=("Arial", 13), foreground=AVIOT_OSCURO, background=AVIOT_BLANCO)
        style.configure("OK.TLabel", font=("Arial", 14, "bold"), foreground=AVIOT_VERDE, background=AVIOT_BLANCO)
        style.configure("Warn.TLabel", font=("Arial", 14, "bold"), foreground=AVIOT_AMBAR, background=AVIOT_BLANCO)
        style.configure("Error.TLabel", font=("Arial", 14, "bold"), foreground=AVIOT_ROJO, background=AVIOT_BLANCO)
        style.configure("Progress.TLabel", font=("Arial", 11), foreground="#888", background=AVIOT_BLANCO)
        style.configure("Aviot.Horizontal.TProgressbar",
                        troughcolor=AVIOT_GRIS, background=AVIOT_NARANJA, thickness=18)

    # ----------------------------- UI -----------------------------
    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=(20, 15, 20, 5))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        # Cabecera
        header = ttk.Frame(top)
        header.grid(row=0, column=0, pady=(0, 8))
        if self.logo_img:
            try:
                self.small_logo = self.logo_img.subsample(
                    max(1, self.logo_img.width() // 180),
                    max(1, self.logo_img.height() // 50))
                ttk.Label(header, image=self.small_logo, background=AVIOT_BLANCO).pack()
            except Exception:
                pass
        ttk.Label(header, text="CONFIGURADOR DE SONDAS", style="Header.TLabel").pack()
        ttk.Label(header, text=f"Temperatura y Humedad  |  Modbus RTU  |  {VERSION}",
                  style="Sub.TLabel").pack()

        tk.Frame(top, height=3, bg=AVIOT_NARANJA).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # --- Conexion ---
        fcon = ttk.LabelFrame(top, text=" Conexion ", padding=10)
        fcon.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        fcon.columnconfigure(1, weight=1)
        ttk.Label(fcon, text="Puerto:", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.combo_puerto = ttk.Combobox(fcon, width=28, font=("Arial", 12), state="readonly")
        self.combo_puerto.grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(fcon, text="Actualizar", command=self.actualizar_puertos).grid(row=0, column=2, padx=5)
        self.btn_conectar = ttk.Button(fcon, text="Conectar", style="Aviot.TButton",
                                        command=self.toggle_conexion)
        self.btn_conectar.grid(row=1, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        self.lbl_estado = ttk.Label(fcon, text="Desconectado", style="Error.TLabel")
        self.lbl_estado.grid(row=2, column=0, columnspan=3, pady=(5, 0))

        # --- Buscar ---
        fbus = ttk.LabelFrame(top, text=" 1. Buscar sonda conectada ", padding=10)
        fbus.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        fbus.columnconfigure(0, weight=1)
        self.btn_buscar = ttk.Button(fbus, text="BUSCAR SONDA", style="Aviot.TButton",
                                     command=self.buscar_sonda)
        self.btn_buscar.grid(row=0, column=0, sticky="ew")
        self.lbl_progreso = ttk.Label(fbus, text="", style="Progress.TLabel")
        self.lbl_progreso.grid(row=1, column=0, pady=(5, 0))
        self.progress = ttk.Progressbar(fbus, length=420, mode='determinate',
                                        style="Aviot.Horizontal.TProgressbar")
        self.progress.grid(row=2, column=0, pady=(5, 0), sticky="ew")
        self.lbl_sonda = ttk.Label(fbus, text="", style="Info.TLabel")
        self.lbl_sonda.grid(row=3, column=0, sticky="w", pady=(5, 0))
        self.lbl_temp = ttk.Label(fbus, text="", style="Info.TLabel")
        self.lbl_temp.grid(row=4, column=0, sticky="w")
        self.lbl_hum = ttk.Label(fbus, text="", style="Info.TLabel")
        self.lbl_hum.grid(row=5, column=0, sticky="w")

        # --- Diagnostico ---
        fdiag = ttk.LabelFrame(top, text=" 2. Diagnostico de la sonda ", padding=10)
        fdiag.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        fdiag.columnconfigure(0, weight=1)
        self.btn_diag = ttk.Button(fdiag, text="DIAGNOSTICO COMPLETO", style="Diag.TButton",
                                   command=self.diagnostico)
        self.btn_diag.grid(row=0, column=0, sticky="ew")
        self.lbl_veredicto = ttk.Label(fdiag, text="Pulsa para comprobar si la sonda mide bien.",
                                       style="Info.TLabel", wraplength=560, justify="left")
        self.lbl_veredicto.grid(row=1, column=0, sticky="w", pady=(8, 0))

        # --- Cambiar ID ---
        fcam = ttk.LabelFrame(top, text=" 3. Cambiar ID ", padding=10)
        fcam.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(fcam, text="Nuevo ID (1-247):", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.spin_id_nuevo = ttk.Spinbox(fcam, from_=1, to=247, width=5, font=("Arial", 14))
        self.spin_id_nuevo.grid(row=0, column=1, padx=5, sticky="w")
        self.spin_id_nuevo.set(2)
        self.btn_cambiar = ttk.Button(fcam, text="CAMBIAR ID", style="Aviot.TButton",
                                      command=self.cambiar)
        self.btn_cambiar.grid(row=0, column=2, padx=5)
        self.lbl_resultado = ttk.Label(fcam, text="", style="Info.TLabel")
        self.lbl_resultado.grid(row=1, column=0, columnspan=3, pady=(10, 0))

        # --- Registro / Log ---
        flog = ttk.LabelFrame(self.root, text=" Registro tecnico (envialo a soporte si hay dudas) ",
                              padding=10)
        flog.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        flog.columnconfigure(0, weight=1)
        flog.rowconfigure(0, weight=1)
        self.txt_log = scrolledtext.ScrolledText(flog, height=10, font=("Consolas", 9),
                                                 bg="#111", fg="#d6d6d6", insertbackground="#fff",
                                                 wrap="none")
        self.txt_log.grid(row=0, column=0, columnspan=4, sticky="nsew")
        self.txt_log.tag_config("ok", foreground="#6fdc6f")
        self.txt_log.tag_config("warn", foreground="#ffc451")
        self.txt_log.tag_config("err", foreground="#ff6b6b")
        self.txt_log.tag_config("info", foreground="#d6d6d6")
        self.txt_log.tag_config("tx", foreground="#7fb3ff")

        barra = ttk.Frame(flog)
        barra.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Button(barra, text="Abrir carpeta de logs", command=self.abrir_carpeta_logs).pack(side="left")
        ttk.Button(barra, text="Copiar log", command=self.copiar_log).pack(side="left", padx=6)
        ttk.Button(barra, text="Limpiar pantalla", command=self.limpiar_log).pack(side="left")
        ttk.Label(barra, text=f"Aviot - Always Safe  |  {VERSION}",
                  font=("Arial", 8), foreground="#aaa", background=AVIOT_BLANCO).pack(side="right")

    # ----------------------------- logging -----------------------------
    def log(self, msg, level="info"):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        try:
            with self._log_lock:
                if self._log_file:
                    self._log_file.write(line + "\n")
                    self._log_file.flush()
        except Exception:
            pass
        self.root.after(0, lambda: self._append_log(line, level))

    def _append_log(self, line, level):
        tag = level if level in ("ok", "warn", "err", "tx") else "info"
        if "TX ->" in line or "RX <-" in line:
            tag = "tx"
        self.txt_log.insert("end", line + "\n", tag)
        self.txt_log.see("end")

    def limpiar_log(self):
        self.txt_log.delete("1.0", "end")

    def copiar_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.txt_log.get("1.0", "end"))
        messagebox.showinfo("Log copiado",
                            "El registro se ha copiado al portapapeles.\n"
                            "Puedes pegarlo en un correo o WhatsApp para soporte.")

    def abrir_carpeta_logs(self):
        carpeta = os.path.dirname(self.log_path)
        try:
            if platform.system() == "Windows":
                os.startfile(carpeta)  # noqa
            elif platform.system() == "Darwin":
                subprocess.run(["open", carpeta])
            else:
                subprocess.run(["xdg-open", carpeta])
        except Exception as e:
            messagebox.showinfo("Carpeta de logs", f"Los logs estan en:\n{carpeta}\n\n({e})")

    # ----------------------------- puertos / conexion -----------------------------
    def actualizar_puertos(self):
        puertos = serial.tools.list_ports.comports()
        encontrados = []
        self.log("Buscando puertos serie...")
        for p in puertos:
            texto = f"{p.device} {p.description} {p.hwid}".lower()
            self.log(f"   Puerto: {p.device}  ({p.description})")
            if any(k in texto for k in ('usb', 'serial', 'ch340', 'cp210', 'ftdi')):
                encontrados.append(f"{p.device} - {p.description}")
        self.combo_puerto['values'] = encontrados if encontrados else ["No se detectan puertos"]
        if encontrados:
            self.combo_puerto.current(0)
            self.log(f"{len(encontrados)} adaptador(es) compatible(s) detectado(s).", "ok")
        else:
            self.log("No se detecta ningun adaptador USB-Serial.", "warn")

    def toggle_conexion(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            self.btn_conectar.config(text="Conectar")
            self.lbl_estado.config(text="Desconectado", style="Error.TLabel")
            self.log("Puerto cerrado.", "warn")
        else:
            puerto = self.combo_puerto.get().split(" - ")[0].strip()
            if not puerto or "No se detectan" in puerto:
                messagebox.showerror("Error", "Conecta el adaptador USB-Modbus y pulsa Actualizar.")
                return
            try:
                self.ser = serial.Serial(port=puerto, baudrate=4800, parity='N',
                                         stopbits=1, bytesize=8, timeout=2)
                self.btn_conectar.config(text="Desconectar")
                self.lbl_estado.config(text=f"Conectado a {puerto}", style="OK.TLabel")
                self.log(f"Puerto abierto: {puerto} @ 4800 8N1.", "ok")
            except serial.SerialException as e:
                messagebox.showerror("Error", f"No se pudo abrir el puerto:\n{e}")
                self.log(f"ERROR abriendo puerto: {e}", "err")

    def check_conexion(self):
        if not self.ser or not self.ser.is_open:
            messagebox.showwarning("Aviso", "Primero conecta el adaptador USB-Modbus.")
            return False
        if self.ocupado:
            messagebox.showwarning("Aviso", "Hay una operacion en curso, espera a que termine.")
            return False
        return True

    # ----------------------------- buscar -----------------------------
    def buscar_sonda(self):
        if self.buscando:
            self.buscando = False
            return
        if not self.check_conexion():
            return

        self.buscando = True
        self.ocupado = True
        self.id_encontrado = None
        self.btn_buscar.config(text="PARAR")
        self.lbl_sonda.config(text="")
        self.lbl_temp.config(text="")
        self.lbl_hum.config(text="")
        self.progress['value'] = 0
        self.progress['maximum'] = 247
        self.log("--- BUSQUEDA DE SONDA (IDs 1-247) ---")

        def worker():
            encontrado = None
            otros = []
            for sid in range(1, 248):
                if not self.buscando:
                    self.log("Busqueda cancelada por el usuario.", "warn")
                    break
                self.root.after(0, lambda s=sid: self._update_progress(s))
                r = leer_sonda_detallado(self.ser, sid, log=self.log, verbose=False)
                if r['ok']:
                    encontrado = r
                    self.log(f"ID {sid}: RESPUESTA VALIDA  "
                             f"Tª={r['temp']}C  HR={r['hum']}%  "
                             f"(reg crudo T=0x{r['raw_temp']:04X} H=0x{r['raw_hum']:04X})", "ok")
                    break
                elif r['resp']:
                    # Respondio algo pero no es una lectura valida: util para diagnostico
                    otros.append(sid)
                    self.log(f"ID {sid}: respuesta no valida ({r['error']})  RX={fmt_hex(r['resp'])}", "warn")

            if encontrado:
                self.id_encontrado = encontrado['slave_id']
                self.root.after(0, lambda r=encontrado: self._sonda_encontrada(r))
            elif self.buscando:
                self.root.after(0, self._sonda_no_encontrada)
                if otros:
                    self.log(f"Hubo respuestas no validas en IDs {otros}. "
                             f"Posible sonda que comunica pero no mide, o ruido en el bus.", "warn")

            self.buscando = False
            self.ocupado = False
            self.root.after(0, lambda: self.btn_buscar.config(text="BUSCAR SONDA"))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, sid):
        self.progress['value'] = sid
        self.lbl_progreso.config(text=f"Probando ID {sid} de 247...")

    def _sonda_encontrada(self, r):
        self.progress['value'] = 247
        self.lbl_progreso.config(text="")
        self.lbl_sonda.config(text=f"Sonda encontrada en ID {r['slave_id']}", style="OK.TLabel")
        self.lbl_temp.config(text=f"Temperatura:  {r['temp']} °C")
        self.lbl_hum.config(text=f"Humedad:       {r['hum']} %")
        if r['raw_temp'] == 0 and r['raw_hum'] == 0:
            self.lbl_sonda.config(
                text=f"Sonda en ID {r['slave_id']} (¡OJO! lectura 0.0/0.0 - pulsa DIAGNOSTICO)",
                style="Warn.TLabel")

    def _sonda_no_encontrada(self):
        self.lbl_progreso.config(text="")
        self.lbl_sonda.config(text="No se encontro ninguna sonda (IDs 1-247)", style="Error.TLabel")
        self.lbl_temp.config(text="")
        self.lbl_hum.config(text="")

    # ----------------------------- diagnostico -----------------------------
    def diagnostico(self):
        if not self.check_conexion():
            return
        if not self.id_encontrado:
            messagebox.showwarning("Aviso", "Primero busca la sonda con 'BUSCAR SONDA'.")
            return

        self.ocupado = True
        self.btn_diag.config(state="disabled")
        self.lbl_veredicto.config(text="Diagnosticando, espera unos segundos...", style="Info.TLabel")
        sid = self.id_encontrado
        N = 6

        def worker():
            self.log(f"--- DIAGNOSTICO COMPLETO (ID {sid}, {N} lecturas) ---")
            lecturas = []
            for i in range(N):
                self.log(f"Lectura {i + 1}/{N}:")
                r = leer_sonda_detallado(self.ser, sid, log=self.log, verbose=True)
                if r['ok']:
                    crc = "CRC OK" if r['crc_ok'] else "CRC ERROR"
                    self.log(f"   -> Tª={r['temp']}C  HR={r['hum']}%  "
                             f"(T=0x{r['raw_temp']:04X} H=0x{r['raw_hum']:04X})  {crc}",
                             "ok" if r['crc_ok'] else "warn")
                else:
                    self.log(f"   -> ERROR: {r['error']}", "err")
                lecturas.append(r)
                time.sleep(0.25)

            # Volcado informativo del mapa de registros
            self.log("Volcado de registros 0x0000-0x0007 (informativo):")
            regs = volcado_registros(self.ser, sid, 8, log=self.log)
            if regs:
                self.log("   Registros: " + "  ".join(f"[{i}]=0x{v:04X}({v})" for i, v in enumerate(regs)))

            self.root.after(0, lambda: self._mostrar_veredicto(lecturas))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_veredicto(self, lecturas):
        self.btn_diag.config(state="normal")
        self.ocupado = False

        validas = [r for r in lecturas if r['ok']]
        con_respuesta = [r for r in lecturas if r['resp']]

        if not con_respuesta:
            txt = ("❌ La sonda NO RESPONDE.\n"
                   "Revisa: cables A+/B- (puede estar invertido), alimentacion 12-24V, "
                   "y que sea la UNICA sonda conectada al bus.")
            style = "Error.TLabel"
            self.log("VEREDICTO: NO RESPONDE.", "err")
        elif not validas:
            err = con_respuesta[0]['error']
            txt = (f"⚠ La sonda responde pero con ERRORES ({err}).\n"
                   "Posible ruido en el bus, baudrate incorrecto o falta resistencia de terminacion.")
            style = "Warn.TLabel"
            self.log(f"VEREDICTO: respuestas con error ({err}).", "warn")
        else:
            todas_cero = all(r['raw_temp'] == 0 and r['raw_hum'] == 0 for r in validas)
            crc_malos = [r for r in validas if r['crc_ok'] is False]
            if todas_cero:
                txt = ("⚠ La sonda COMUNICA pero el SENSOR NO MIDE.\n"
                       f"Las {len(validas)} lecturas dan 0.0 °C y 0.0 % (registros en cero). "
                       "El elemento sensor interno esta averiado: esta sonda NO es utilizable. "
                       "Casi seguro es una de las retiradas por defectuosas.")
                style = "Warn.TLabel"
                self.log("VEREDICTO: COMUNICA PERO NO MIDE (sensor averiado). Sonda no utilizable.", "warn")
            elif crc_malos:
                txt = ("⚠ Lecturas con CRC erroneo. La comunicacion tiene ruido.\n"
                       "Revisa cableado/terminacion del bus y vuelve a probar.")
                style = "Warn.TLabel"
                self.log("VEREDICTO: lecturas con CRC erroneo.", "warn")
            else:
                temps = [r['temp'] for r in validas]
                hums = [r['hum'] for r in validas]
                txt = (f"✅ SONDA CORRECTA.\n"
                       f"Temperatura: {min(temps)}–{max(temps)} °C   |   "
                       f"Humedad: {min(hums)}–{max(hums)} %\n"
                       "Mide y comunica bien. Puedes instalarla.")
                style = "OK.TLabel"
                self.log(f"VEREDICTO: SONDA CORRECTA (T={temps}, HR={hums}).", "ok")

        self.lbl_veredicto.config(text=txt, style=style)

    # ----------------------------- cambiar ID -----------------------------
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
        if not messagebox.askyesno("Confirmar", f"¿Cambiar ID de {self.id_encontrado} a {id_nuevo}?"):
            return

        self.lbl_resultado.config(text="Cambiando ID...", style="Info.TLabel")
        self.root.update()
        self.log(f"--- CAMBIO DE ID {self.id_encontrado} -> {id_nuevo} ---")

        ok = cambiar_id_sonda(self.ser, self.id_encontrado, id_nuevo, log=self.log)
        if not ok:
            self.lbl_resultado.config(text="Error al enviar comando", style="Error.TLabel")
            self.log("Error: la sonda no confirmo el cambio de ID.", "err")
            return

        time.sleep(1)
        r = leer_sonda_detallado(self.ser, id_nuevo, log=self.log, verbose=True)
        if r['ok']:
            self.id_encontrado = id_nuevo
            self.lbl_sonda.config(text=f"Sonda encontrada en ID {id_nuevo}", style="OK.TLabel")
            aviso = ""
            if r['raw_temp'] == 0 and r['raw_hum'] == 0:
                aviso = "  ¡OJO! lectura 0.0/0.0, revisa con DIAGNOSTICO."
            self.lbl_resultado.config(
                text=f"ID cambiado a {id_nuevo}  ({r['temp']}°C, {r['hum']}%).{aviso}",
                style="Warn.TLabel" if aviso else "OK.TLabel")
            self.log(f"ID cambiado correctamente a {id_nuevo}. "
                     f"Lectura: {r['temp']}C / {r['hum']}%.", "ok")
        else:
            self.lbl_resultado.config(text="Comando enviado pero no responde en nuevo ID",
                                      style="Error.TLabel")
            self.log(f"Aviso: no responde en el nuevo ID {id_nuevo} ({r['error']}).", "err")

    # ----------------------------- cierre -----------------------------
    def _on_close(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        try:
            if self._log_file:
                self._log_file.close()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
