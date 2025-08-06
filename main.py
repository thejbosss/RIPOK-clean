import customtkinter as ctk
from PIL import Image
import os
import subprocess
import time
import threading
from datetime import datetime, timedelta

# Configuración inicial
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ventana = ctk.CTk()
ventana.title("PTCGP BOT SUITE")
ventana.geometry("800x550")
ventana.resizable(False, False)

accounts_folder = r"C:\Users\thepo\Desktop\Bots\PTCGPB-CROWNS\Accounts\Saved\1"

color_normal = "#007BFF"
color_hover = "#339DFF"
color_active = "#0051C7"
borde_activo = "#003D99"

botones = []
boton_activo = None
bot_en_marcha = False
cuentas_cursadas = 0

inicio_total = None
duraciones_cuentas = []
inicio_cuenta = None
actualizando_tiempo = False  # NUEVO

accounts_botted_val = None
total_time_val = None
average_time_val = None

# --- Funciones nuevas para tiempo en vivo ---
# Función integrada: lanzar_segundo_script


def lanzar_segundo_script(nombre_cuenta_sin_ext, done_event=None):
    ruta_script = r"C:\Proyec\research\PokemonTCG-Research\Frida\frida_server_mv_emu1.py"
    comando = ["python", ruta_script, nombre_cuenta_sin_ext]

    def hilo_lanzador():
        try:
            proceso = subprocess.Popen(
                comando,
                stdout=None,
                stderr=None
            )

            proceso.wait()

            if done_event:
                done_event.set()

            log_box.configure(state="normal")
            log_box.insert("end", f"✅ Data extractor finished for account: {nombre_cuenta_sin_ext}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

        except Exception as e:
            if done_event:
                done_event.set()

            log_box.configure(state="normal")
            log_box.insert("end", f"❌ Error en segundo script:\n{str(e)}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

    threading.Thread(target=hilo_lanzador, daemon=True).start()

    log_box.configure(state="normal")
    log_box.insert("end", f"▶️ Lanzado extractor con cuenta: {nombre_cuenta_sin_ext}\n")
    log_box.see("end")
    log_box.configure(state="disabled")


def format_hms(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}"

def actualizar_tiempo_total():
    global inicio_total, actualizando_tiempo
    if inicio_total is None or not actualizando_tiempo:
        return
    ahora = time.time()
    transcurrido = ahora - inicio_total
    if total_time_val:
        total_time_val.configure(text=format_hms(transcurrido))
    ventana.after(1000, actualizar_tiempo_total)

def lanzar_macro_airtest(xml_inyectado=None):
    macro_path = r"C:\Proyec\airt\test1_emu1.air"
    env_python = r"C:\Proyec\airt\air_env\Scripts\python.exe"
    script_path = os.path.join(macro_path, "test1_emu1.py")

    def leer_salida(proceso):
        global cuentas_cursadas, inicio_cuenta, duraciones_cuentas
        global accounts_botted_val, total_time_val, average_time_val

        # Obtenemos el nombre de cuenta sin extensión para pasarlo al segundo script
        nombre_cuenta_sin_ext = None
        if xml_inyectado:
            nombre_cuenta_sin_ext = os.path.splitext(os.path.basename(xml_inyectado))[0]

        for line in proceso.stdout:
            log_box.configure(state="normal")
            log_box.insert("end", f"📤 Bot: {line.strip()}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

            # Detectar trigger para lanzar el segundo script, sin modificar flujo original
            if "In home" in line and nombre_cuenta_sin_ext:
                frida_done_event = threading.Event()
                lanzar_segundo_script(nombre_cuenta_sin_ext, done_event=frida_done_event)
                frida_done_event.wait(timeout=90)  # espera a que Frida termine (máx 30s)

        # Esperar que termine el primer script (si no lo hizo aún)
        proceso.wait()

        if xml_inyectado and os.path.exists(xml_inyectado):
            os.utime(xml_inyectado, None)
            log_box.configure(state="normal")
            log_box.insert("end", f"🕒 Modification date updated for {os.path.basename(xml_inyectado)}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

        # Aquí añadimos la llamada para hacer pull de cache y userpref al terminar la cuenta
        log_box.configure(state="normal")
        log_box.insert("end", "⏳ Waiting 2 seconds before starting the bot...\n")
        log_box.see("end")
        log_box.configure(state="disabled")
        cuentas_cursadas += 1

        fin_cuenta = time.time()
        duracion = fin_cuenta - inicio_cuenta
        duraciones_cuentas.append(duracion)

        cuentas_botteadas = len(duraciones_cuentas)
        total_time = sum(duraciones_cuentas)
        average_time = total_time / cuentas_botteadas if cuentas_botteadas > 0 else 0

        def format_time(seconds):
            m, s = divmod(int(seconds), 60)
            h, m = divmod(m, 60)
            return f"{h:02}:{m:02}:{s:02}" if h > 0 else f"{m}:{s:02}"

        accounts_botted_val.configure(text=f"{cuentas_botteadas}")
        avg_m, avg_s = divmod(int(average_time), 60)
        average_time_val.configure(text=f"{avg_m:02}:{avg_s:02} (mm/ss)")

        time.sleep(2)
        iniciar_bot()

    try:
        proceso = subprocess.Popen(
            [env_python, "-u", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        hilo_salida = threading.Thread(target=leer_salida, args=(proceso,))
        hilo_salida.start()

        log_box.configure(state="normal")
        log_box.insert("end", "✅ Bot running...\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    except Exception as e:
        log_box.configure(state="normal")
        log_box.insert("end", f"❌ Error al lanzar macro Airtest:\n{str(e)}\n")
        log_box.see("end")
        log_box.configure(state="disabled")
# Función para comprobar si frida-server está activo en el emulador
def frida_server_esta_activo():
    try:
        resultado = subprocess.run(
            ["adb", "-s", "127.0.0.1:5555", "shell", "su", "-c", "pidof", "sv64"],
            capture_output=True,
            text=True
        )
        return resultado.returncode == 0 and resultado.stdout.strip() != ""
    except Exception:
        return False       

def iniciar_bot():
    global bot_en_marcha, inicio_cuenta, inicio_total, actualizando_tiempo
    bot_en_marcha = True

    # Inicio del contador total en tiempo real
    if inicio_total is None:
        inicio_total = time.time()
        actualizando_tiempo = True
        actualizar_tiempo_total()

    start_btn.configure(border_width=2, border_color=color_active)
    pause_btn.configure(state="normal")
    log_box.configure(state="normal")
    log_box.insert("end", "▶️ Bot iniciado\n")
    log_box.see("end")
    log_box.configure(state="disabled")
    actualizar_barra()

    ahora = datetime.now()
    archivos_xml = []

    for archivo in os.listdir(accounts_folder):
        if archivo.lower().endswith(".xml"):
            ruta = os.path.join(accounts_folder, archivo)
            modificado = datetime.fromtimestamp(os.path.getmtime(ruta))
            if ahora - modificado > timedelta(hours=24):
                archivos_xml.append((ruta, modificado))

    if archivos_xml:
        archivos_xml.sort(key=lambda x: x[1])
        primer_botable = archivos_xml[0][0]

        inicio_cuenta = time.time()

        log_box.configure(state="normal")
        log_box.delete("1.0", "end")  # <-- Borra todo el log
        log_box.insert("end", f"📄 Selected account: {os.path.basename(primer_botable)}\n")
        log_box.insert("end", "🚀 Starting ADB Commands...\n")
        log_box.see("end")
        log_box.configure(state="disabled")

        ADB_COMMANDS_TEMPLATE = [
            
            ["adb", "-s", "127.0.0.1:5555", "shell", "am", "force-stop", "jp.pokemon.pokemontcgp"],
            ["adb", "-s", "127.0.0.1:5555", "root"],
            # --- comandos para abrir info app y hacer tap en borrar cache y missionuserprefs---
            ["adb", "-s", "127.0.0.1:5555", "shell", "su", "-c", "chmod -R 777 /data/data/jp.pokemon.pokemontcgp/cache"],
            ["adb", "-s", "127.0.0.1:5555", "shell", "su", "-c", "rm -rf /data/data/jp.pokemon.pokemontcgp/cache/*"],
            ["adb", "-s", "127.0.0.1:5555", "shell", "su", "-c", "rm -rf /data/data/jp.pokemon.pokemontcgp/cache/WebView"],
            ["adb", "-s", "127.0.0.1:5555", "shell", "su", "-c", "rm", "-f", "/data/data/jp.pokemon.pokemontcgp/files/UserPreferences/v1/MissionUserPrefs"],
             # ---------------------------------------------------------------
            ["adb", "-s", "127.0.0.1:5555", "push", primer_botable, "/sdcard/deviceAccount.xml"],
            ["adb", "-s", "127.0.0.1:5555", "shell", "su", "-c", "cp", "/sdcard/deviceAccount.xml", "/data/data/jp.pokemon.pokemontcgp/shared_prefs/deviceAccount:.xml"],
            ["adb", "-s", "127.0.0.1:5555", "shell", "su", "-c", "chmod", "664", "/data/data/jp.pokemon.pokemontcgp/shared_prefs/deviceAccount:.xml"],
            ["adb", "-s", "127.0.0.1:5555", "shell", "rm", "/sdcard/deviceAccount.xml"],
            ["adb", "-s", "127.0.0.1:5555", "shell", "am", "start", "-n", "jp.pokemon.pokemontcgp/com.unity3d.player.UnityPlayerActivity"]
        ]

        errores = []

        for comando in ADB_COMMANDS_TEMPLATE:
            try:
                resultado = subprocess.run(comando, capture_output=True, text=True)
                if resultado.returncode != 0:
                    errores.append(f"❌ Error: {' '.join(comando)}\n{resultado.stderr.strip()}")
                time.sleep(0.5)
            except Exception as e:
                errores.append(f"❌ Exception ejecutando: {' '.join(comando)}\n{str(e)}")

        log_box.configure(state="normal")
        if errores:
            for err in errores:
                log_box.insert("end", f"{err}\n")
        else:
            log_box.insert("end", "✅ ADB Commands completed successfully\n")
            log_box.see("end")
            # Lanzar frida-server solo la primera vez (sin modificar nada más)
            global frida_server_lanzado
            if not globals().get("frida_server_lanzado", False):
                try:
                    subprocess.run([
                        "adb", "-s", "127.0.0.1:5555",
                        "shell", "su", "-c", "killall sv64"
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    # Breve pausa opcional (puede ayudar a evitar "stale socket" si vas muy rápido)
                    time.sleep(1)
                    subprocess.Popen(
                        ["adb", "-s", "127.0.0.1:5555", "shell", "su", "-c", "/data/local/tmp/sv64 &"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    log_box.insert("end", "▶️ Emu data extractor ON\n")
                    frida_server_lanzado = False
                except Exception as e:
                    log_box.insert("end", f"❌ Error al iniciar frida-server:\n{e}\n")
            else:
                # Aquí añadimos la comprobación y log de si frida-server está activo
                if frida_server_esta_activo():
                    log_box.insert("end", "ℹ️ Emu data extractor is now active on the emulator\n")
                else:
                    log_box.insert("end", "⚠️ Frida-server no está activo pero no se intentó reiniciar\n")
            lanzar_macro_airtest(primer_botable)
        log_box.configure(state="disabled")

    else:
        log_box.configure(state="normal")
        log_box.insert("end", "⛔ No se encontró ninguna cuenta botable (XML >24h)\n")
        log_box.see("end")
        log_box.configure(state="disabled")
        
def pausar_bot():
    global bot_en_marcha
    bot_en_marcha = False
    start_btn.configure(border_width=0)
    pause_btn.configure(state="disabled")
    log_box.configure(state="normal")
    log_box.insert("end", "⏸ Bot pausado\n")
    log_box.see("end")
    log_box.configure(state="disabled")

def actualizar_barra():
    if botable_xml > 0:
        porcentaje = cuentas_cursadas / botable_xml
    else:
        porcentaje = 0
    progreso.set(porcentaje)
    progreso_text.configure(text=f"{cuentas_cursadas} / {botable_xml}")

def cambiar_contenido(seccion):
    global boton_activo, pause_btn, start_btn, log_box, botable_xml, progreso, progreso_text
    global accounts_botted_val, total_time_val, average_time_val

    for widget in contenido_frame.winfo_children():
        widget.destroy()

    if seccion == "Bot":
        titulo = ctk.CTkLabel(contenido_frame, text="PCGTP BOT SUITE > BOT", text_color="#003D99", font=("Consolas", 16, "bold"), anchor="w", justify="left")
        titulo.pack(pady=(15, 5), padx=15, anchor="w")

        ruta_contenedor = ctk.CTkFrame(contenido_frame, fg_color="transparent")
        ruta_contenedor.pack(pady=(0, 10), padx=15, fill="x")
        ruta_label = ctk.CTkLabel(ruta_contenedor, text="Accounts Folder:", font=("Consolas", 12, "bold"))
        ruta_label.pack(side="left")
        ruta_valor = ctk.CTkLabel(ruta_contenedor, text=accounts_folder, font=("Consolas", 12))
        ruta_valor.pack(side="left", padx=(5, 0))

        total_xml = 0
        botable_xml = 0
        try:
            archivos = os.listdir(accounts_folder)
            ahora = datetime.now()
            for archivo in archivos:
                if archivo.lower().endswith(".xml"):
                    total_xml += 1
                    ruta = os.path.join(accounts_folder, archivo)
                    modificado = datetime.fromtimestamp(os.path.getmtime(ruta))
                    if ahora - modificado > timedelta(hours=24):
                        botable_xml += 1
        except Exception as e:
            print("Error al leer carpeta:", e)

        stats_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=15, pady=(0, 5))

        left_stats = ctk.CTkFrame(stats_frame, fg_color="transparent")
        left_stats.pack(side="left")

        total_label = ctk.CTkLabel(left_stats, text="Total Accounts:", font=("Consolas", 12, "bold"))
        total_label.pack(side="left", padx=(0, 5))
        total_value = ctk.CTkLabel(left_stats, text=f"{total_xml}", font=("Consolas", 12))
        total_value.pack(side="left", padx=(0, 20))

        botables_label = ctk.CTkLabel(left_stats, text="Botable Accounts (24h+):", font=("Consolas", 12, "bold"))
        botables_label.pack(side="left", padx=(0, 5))
        botables_value = ctk.CTkLabel(left_stats, text=f"{botable_xml}", font=("Consolas", 12))
        botables_value.pack(side="left")

        right_buttons = ctk.CTkFrame(stats_frame, fg_color="transparent")
        right_buttons.pack(side="right")

        start_btn = ctk.CTkButton(right_buttons, text="Start Bot", width=90, height=24,
                                  fg_color="black", hover_color="#333", text_color="white",
                                  font=("Consolas", 10), command=iniciar_bot)
        start_btn.pack(side="left", padx=5)

        pause_btn = ctk.CTkButton(right_buttons, text="Pause Bot", width=90, height=24,
                                  fg_color="black", hover_color="#333", text_color="white",
                                  font=("Consolas", 10), command=pausar_bot, state="disabled")
        pause_btn.pack(side="left", padx=5)

        log_label = ctk.CTkLabel(contenido_frame, text="LOG", font=("Consolas", 12, "bold"))
        log_label.pack(pady=(2, 0), padx=15, anchor="w")

        log_frame = ctk.CTkFrame(contenido_frame, fg_color="black", corner_radius=8)
        log_frame.pack(padx=12, pady=(0, 6), fill="x")

        log_box = ctk.CTkTextbox(log_frame, height=200, fg_color="black",
                                 text_color="#339DFF", font=("Consolas", 11))
        log_box.pack(fill="both", expand=True, padx=8, pady=6)
        log_box.insert("end", "⏳ Esperando acción...\n")
        log_box.see("end")
        log_box.configure(state="disabled")

        progress_label = ctk.CTkLabel(contenido_frame, text="PROGRESS", font=("Consolas", 12, "bold"))
        progress_label.pack(pady=(8, 0), padx=15, anchor="w")

        progreso = ctk.DoubleVar(value=0.0)
        barra = ctk.CTkProgressBar(contenido_frame, height=14, corner_radius=6,
                                   progress_color="#007BFF", variable=progreso)
        barra.pack(padx=15, fill="x")

        progreso_text = ctk.CTkLabel(barra, text="", font=("Consolas", 11, "bold"),
                                     text_color="white", fg_color="transparent")
        progreso_text.place(relx=0.5, rely=0.5, anchor="center")

        stats_label = ctk.CTkLabel(contenido_frame, text="STATS", font=("Consolas", 12, "bold"))
        stats_label.pack(pady=(6, 0), padx=15, anchor="w")
        stats_row = ctk.CTkFrame(contenido_frame, fg_color="transparent")
        stats_row.pack(padx=15, pady=(4, 6), fill="x")

        accounts_botted_lbl = ctk.CTkLabel(stats_row, text="Accounts Botted:", font=("Consolas", 12, "bold"))
        accounts_botted_lbl.pack(side="left", padx=(0,5))
        accounts_botted_val = ctk.CTkLabel(stats_row, text="0", font=("Consolas", 12))
        accounts_botted_val.pack(side="left", padx=(0,20))

        total_time_lbl = ctk.CTkLabel(stats_row, text="Total Time:", font=("Consolas", 12, "bold"))
        total_time_lbl.pack(side="left", padx=(0,5))
        total_time_val = ctk.CTkLabel(stats_row, text="00:00:00", font=("Consolas", 12))
        total_time_val.pack(side="left", padx=(0,20))

        average_time_lbl = ctk.CTkLabel(stats_row, text="Average Time:", font=("Consolas", 12, "bold"))
        average_time_lbl.pack(side="left", padx=(0,5))
        average_time_val = ctk.CTkLabel(stats_row, text="0:00 (mm/ss)", font=("Consolas", 12))
        average_time_val.pack(side="left", padx=(0,20))

        actualizar_barra()

    if boton_activo:
        boton_activo.configure(fg_color=color_normal, border_width=0, font=("Consolas", 13))

    for b in botones:
        if b.cget("text") == seccion:
            b.configure(fg_color=color_active, border_width=2,
                        border_color=borde_activo, font=("Consolas", 13, "bold"))
            boton_activo = b
            break

menu_frame = ctk.CTkFrame(ventana, width=160, corner_radius=0, fg_color="white")
menu_frame.pack(side="left", fill="y")

try:
    logo = ctk.CTkImage(Image.open("assets/logo.png"), size=(70, 70))
    logo_label = ctk.CTkLabel(menu_frame, image=logo, text="", fg_color="white")
    logo_label.pack(pady=(20, 0))
except Exception as e:
    print("Logo no encontrado:", e)

titulo = ctk.CTkLabel(menu_frame, text="PTCGP BOT SUITE", font=("Consolas", 8, "bold"),
                      text_color="#333", anchor="center")
titulo.pack(pady=(2, 10))

secciones = ["Bot", "Accounts", "Stats", "Tools"]
for seccion in secciones:
    boton = ctk.CTkButton(menu_frame, text=seccion,
                          command=lambda s=seccion: cambiar_contenido(s),
                          fg_color=color_normal, hover_color=color_hover,
                          text_color="white", font=("Consolas", 13),
                          corner_radius=6, height=35)
    boton.pack(pady=4, padx=12, fill="x")
    botones.append(boton)

contenido_frame = ctk.CTkFrame(ventana, fg_color="#f4f4f4")
contenido_frame.pack(side="left", fill="both", expand=True)

ventana.mainloop()
