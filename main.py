import customtkinter as ctk
from PIL import Image
import os
import subprocess
import time
import threading
from datetime import datetime, timedelta
import shutil

# Configuración inicial
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ventana = ctk.CTk()
ventana.title("PTCGP BOT SUITE")
ventana.geometry("800x550")
ventana.resizable(False, False)

accounts_folder = r"C:\Users\thepo\Desktop\Bots\PTCGPB-CROWNS\Accounts\Saved\1"
#accounts_folder = r"C:\Users\thepo\Desktop\Bots\PTCGPB-RESTO\Accounts\Saved\1"
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

# Carpetas para cache y userpref locales
CACHE_BASE_FOLDER = r"C:\Proyec\PTCGP_BOT_SUITE\data\PBS\emucache"
USERPREF_BASE_FOLDER = r"C:\Proyec\PTCGP_BOT_SUITE\data\PBS\emuuserpref"

# --- Funciones nuevas para tiempo en vivo ---

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

# Función para comprobar si frida-server está activo en el emulador
def frida_server_esta_activo():
    try:
        resultado = subprocess.run(
            ["adb", "-s", "emulator-5554", "shell", "pidof", "sv64"],
            capture_output=True,
            text=True
        )
        return resultado.returncode == 0 and resultado.stdout.strip() != ""
    except Exception:
        return False

# Función integrada: lanzar_segundo_script
def lanzar_segundo_script(nombre_cuenta_sin_ext):
    ruta_script = r"C:\Proyec\research\PokemonTCG-Research\Frida\frida_server_mv.py"
    comando = ["python", ruta_script, nombre_cuenta_sin_ext]

    try:
        log_box.configure(state="normal")
        log_box.insert("end", f"▶️ Lanzando segundo script con cuenta: {nombre_cuenta_sin_ext}\n")
        log_box.see("end")
        log_box.configure(state="disabled")

        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",      # <-- Forzamos UTF-8
            errors="replace"       # <-- Reemplaza cualquier carácter problemático
        )

        for linea in proceso.stdout:
            log_box.configure(state="normal")
            log_box.insert("end", f"📤 Data extractor: {linea.strip()}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

        proceso.wait()

        log_box.configure(state="normal")
        log_box.insert("end", f"✅ Data extractor finished for account: {nombre_cuenta_sin_ext}\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    except Exception as e:
        log_box.configure(state="normal")
        log_box.insert("end", f"❌ Error al lanzar segundo script:\n{str(e)}\n")
        log_box.see("end")
        log_box.configure(state="disabled")

def push_cache_y_userpref(nombre_cuenta_sin_ext):
    carpeta_cache_local = os.path.join(CACHE_BASE_FOLDER, nombre_cuenta_sin_ext, '.')
    carpeta_userpref_local = os.path.join(USERPREF_BASE_FOLDER, nombre_cuenta_sin_ext, '.')

    # Limpiar en emulador los datos previos para evitar conflictos
    comandos_borrar = [
        ["adb", "-s", "emulator-5554", "shell", "am", "force-stop", "jp.pokemon.pokemontcgp"],
        ["adb", "-s", "emulator-5554", "shell", "rm", "-f", "/data/data/jp.pokemon.pokemontcgp/files/UserPreferences/v1/MissionUserPrefs"],
        ["adb", "-s", "emulator-5554", "shell", "rm", "-rf", "/data/data/jp.pokemon.pokemontcgp/cache/*"]
    ]
    for cmd in comandos_borrar:
        try:
            resultado = subprocess.run(cmd, capture_output=True, text=True)
            log_box.configure(state="normal")
            log_box.insert("end", "Closing App and cache clear\n")
            log_box.see("end")
            log_box.configure(state="disabled")
            if resultado.returncode != 0:
                log_box.configure(state="normal")
                log_box.insert("end", f"⚠️ Error limpiando datos previos en emulador: {' '.join(cmd)}\n{resultado.stderr.strip()}\n")
                log_box.see("end")
                log_box.configure(state="disabled")
        except Exception as e:
            log_box.configure(state="normal")
            log_box.insert("end", f"⚠️ Excepción limpiando datos previos en emulador: {' '.join(cmd)}\n{str(e)}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

    if not (os.path.isdir(carpeta_cache_local) and os.path.isdir(carpeta_userpref_local)):
        # No existen ambas carpetas, no hacemos push para evitar errores
        log_box.configure(state="normal")
        log_box.insert("end", f"ℹ️ No local cache/userpref folders exist for account '{nombre_cuenta_sin_ext}'.\n")
        log_box.see("end")
        log_box.configure(state="disabled")
        return

    # Push MissionUserPrefs
    mission_userpref_path = os.path.join(carpeta_userpref_local, "MissionUserPrefs")
    if os.path.isfile(mission_userpref_path):
        cmd_push_userpref = [
            "adb", "-s", "emulator-5554", "push",
            mission_userpref_path,
            "/data/data/jp.pokemon.pokemontcgp/files/UserPreferences/v1"
        ]
        try:
            resultado = subprocess.run(cmd_push_userpref, capture_output=True, text=True)
            if resultado.returncode == 0:
                log_box.configure(state="normal")
                log_box.insert("end", f"✅ Push MissionUserPrefs for '{nombre_cuenta_sin_ext}' completado\n")
                log_box.see("end")
                log_box.configure(state="disabled")
            else:
                log_box.configure(state="normal")
                log_box.insert("end", f"❌ Error push MissionUserPrefs para '{nombre_cuenta_sin_ext}': {resultado.stderr.strip()}\n")
                log_box.see("end")
                log_box.configure(state="disabled")
        except Exception as e:
            log_box.configure(state="normal")
            log_box.insert("end", f"❌ Excepción push MissionUserPrefs para '{nombre_cuenta_sin_ext}': {str(e)}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
    else:
        log_box.configure(state="normal")
        log_box.insert("end", f"⚠️ No existe MissionUserPrefs local para '{nombre_cuenta_sin_ext}'\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    # Push carpeta cache completa (en adb push, al hacer push a carpeta, se copia contenido dentro)
    cmd_push_cache = [
        "adb", "-s", "emulator-5554", "push",
        carpeta_cache_local,
        "/data/data/jp.pokemon.pokemontcgp/cache"
    ]
    try:
        resultado = subprocess.run(cmd_push_cache, capture_output=True, text=True)
        if resultado.returncode == 0:
            log_box.configure(state="normal")
            log_box.insert("end", f"✅ Push cache for '{nombre_cuenta_sin_ext}' complete\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        else:
            log_box.configure(state="normal")
            log_box.insert("end", f"❌ Error push cache para '{nombre_cuenta_sin_ext}': {resultado.stderr.strip()}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
    except Exception as e:
        log_box.configure(state="normal")
        log_box.insert("end", f"❌ Excepción push cache para '{nombre_cuenta_sin_ext}': {str(e)}\n")
        log_box.see("end")
        log_box.configure(state="disabled")

def pull_cache_y_userpref(nombre_cuenta_sin_ext):
    """
    Después de terminar la cuenta, hacer pull de cache y MissionUserPrefs para guardarlos localmente.
    Crear carpetas si no existen.
    """
    carpeta_cache_local = os.path.join(CACHE_BASE_FOLDER, nombre_cuenta_sin_ext)
    carpeta_userpref_local = os.path.join(USERPREF_BASE_FOLDER, nombre_cuenta_sin_ext)

    # BORRAR carpeta cache local antes de pull para evitar subcarpetas anidadas
    if os.path.exists(carpeta_cache_local):
        try:
            shutil.rmtree(carpeta_cache_local)
            log_box.configure(state="normal")
            log_box.insert("end", f"🗑️ Local cahce clear: {carpeta_cache_local}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        except Exception as e:
            log_box.configure(state="normal")
            log_box.insert("end", f"❌ Error borrando cache local antes del pull: {str(e)}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

    # Crear carpetas si no existen
    if not os.path.exists(carpeta_cache_local):
        try:
            os.makedirs(carpeta_cache_local)
            log_box.configure(state="normal")
            log_box.insert("end", f"🆕 Local cache folder : {carpeta_cache_local}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        except Exception as e:
            log_box.configure(state="normal")
            log_box.insert("end", f"❌ Error creando carpeta cache local: {str(e)}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

    if not os.path.exists(carpeta_userpref_local):
        try:
            os.makedirs(carpeta_userpref_local)
            log_box.configure(state="normal")
            log_box.insert("end", f"🆕 Local userpref folder created: {carpeta_userpref_local}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        except Exception as e:
            log_box.configure(state="normal")
            log_box.insert("end", f"❌ Error creando carpeta userpref local: {str(e)}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

    # Pull MissionUserPrefs
    cmd_pull_userpref = [
        "adb", "-s", "emulator-5554", "pull",
        "/data/data/jp.pokemon.pokemontcgp/files/UserPreferences/v1/.",
        carpeta_userpref_local
    ]
    try:
        resultado = subprocess.run(cmd_pull_userpref, capture_output=True, text=True)
        if resultado.returncode == 0:
            log_box.configure(state="normal")
            log_box.insert("end", f"✅ Pull MissionUserPrefs for '{nombre_cuenta_sin_ext}' complete\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        else:
            log_box.configure(state="normal")
            log_box.insert("end", f"❌ Error pull MissionUserPrefs para '{nombre_cuenta_sin_ext}': {resultado.stderr.strip()}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
    except Exception as e:
        log_box.configure(state="normal")
        log_box.insert("end", f"❌ Excepción pull MissionUserPrefs para '{nombre_cuenta_sin_ext}': {str(e)}\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    # Pull carpeta cache completa
    cmd_pull_cache = [
        "adb", "-s", "emulator-5554", "pull",
        "/data/data/jp.pokemon.pokemontcgp/cache/.",
        carpeta_cache_local
    ]
    try:
        resultado = subprocess.run(cmd_pull_cache, capture_output=True, text=True)
        if resultado.returncode == 0:
            log_box.configure(state="normal")
            log_box.insert("end", f"✅ Pull cache for '{nombre_cuenta_sin_ext}' complete\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        else:
            log_box.configure(state="normal")
            log_box.insert("end", f"❌ Error pull cache para '{nombre_cuenta_sin_ext}': {resultado.stderr.strip()}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
    except Exception as e:
        log_box.configure(state="normal")
        log_box.insert("end", f"❌ Excepción pull cache para '{nombre_cuenta_sin_ext}': {str(e)}\n")
        log_box.see("end")
        log_box.configure(state="disabled")


def lanzar_macro_airtest(xml_inyectado=None):
    macro_path = r"C:\Proyec\airt\test1.air"
    env_python = r"C:\Proyec\airt\air_env\Scripts\python.exe"
    script_path = os.path.join(macro_path, "test1.py")

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
                # Lanzar el segundo script y esperar a que termine antes de seguir
                lanzar_segundo_script(nombre_cuenta_sin_ext)

        # Esperar que termine el primer script (si no lo hizo aún)
        proceso.wait()

        if xml_inyectado and os.path.exists(xml_inyectado):
            os.utime(xml_inyectado, None)
            log_box.configure(state="normal")
            log_box.insert("end", f"🕒 Modification date updated for {os.path.basename(xml_inyectado)}\n")
            log_box.see("end")
            log_box.configure(state="disabled")

        # Aquí añadimos la llamada para hacer pull de cache y userpref al terminar la cuenta
        if nombre_cuenta_sin_ext:
            pull_cache_y_userpref(nombre_cuenta_sin_ext)

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

        nombre_cuenta_sin_ext = os.path.splitext(os.path.basename(primer_botable))[0]
        # PUSH cache y userpref antes de iniciar la cuenta
        push_cache_y_userpref(nombre_cuenta_sin_ext)
        
        ADB_COMMANDS_TEMPLATE = [
            ["adb", "-s", "emulator-5554", "push", primer_botable, "/sdcard/deviceAccount.xml"],
            ["adb", "-s", "emulator-5554", "root"],
            ["adb", "-s", "emulator-5554", "shell", "cp", "/sdcard/deviceAccount.xml", "/data/data/jp.pokemon.pokemontcgp/shared_prefs/deviceAccount:.xml"],
            ["adb", "-s", "emulator-5554", "shell", "chmod", "664", "/data/data/jp.pokemon.pokemontcgp/shared_prefs/deviceAccount:.xml"],
            ["adb", "-s", "emulator-5554", "shell", "rm", "/sdcard/deviceAccount.xml"],
            # NOTA: No borramos aquí MissionUserPrefs ni cache, porque los acabamos de hacer push si existían
            ["adb", "-s", "emulator-5554", "shell", "am", "start", "-n", "jp.pokemon.pokemontcgp/com.unity3d.player.UnityPlayerActivity"]
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
                    subprocess.Popen(
                        ["adb", "-s", "emulator-5554", "shell", "su", "-c", "/data/local/tmp/sv64 &"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    log_box.insert("end", "▶️ Emu data extractor ON\n")
                    frida_server_lanzado = True
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
        global botable_xml
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

        global log_box
        log_box = ctk.CTkTextbox(log_frame, height=200, fg_color="black",
                                 text_color="#339DFF", font=("Consolas", 11))
        log_box.pack(fill="both", expand=True, padx=8, pady=6)
        log_box.insert("end", "⏳ Esperando acción...\n")
        log_box.see("end")
        log_box.configure(state="disabled")

        progress_label = ctk.CTkLabel(contenido_frame, text="PROGRESS", font=("Consolas", 12, "bold"))
        progress_label.pack(pady=(8, 0), padx=15, anchor="w")

        global progreso
        progreso = ctk.DoubleVar(value=0.0)
        barra = ctk.CTkProgressBar(contenido_frame, height=14, corner_radius=6,
                                   progress_color="#007BFF", variable=progreso)
        barra.pack(padx=15, fill="x")

        global progreso_text
        progreso_text = ctk.CTkLabel(barra, text="", font=("Consolas", 11, "bold"),
                                     text_color="white", fg_color="transparent")
        progreso_text.place(relx=0.5, rely=0.5, anchor="center")

        stats_label = ctk.CTkLabel(contenido_frame, text="STATS", font=("Consolas", 12, "bold"))
        stats_label.pack(pady=(6, 0), padx=15, anchor="w")
        stats_row = ctk.CTkFrame(contenido_frame, fg_color="transparent")
        stats_row.pack(padx=15, pady=(4, 6), fill="x")

        global accounts_botted_val
        accounts_botted_lbl = ctk.CTkLabel(stats_row, text="Accounts Botted:", font=("Consolas", 12, "bold"))
        accounts_botted_lbl.pack(side="left", padx=(0,5))
        accounts_botted_val = ctk.CTkLabel(stats_row, text="0", font=("Consolas", 12))
        accounts_botted_val.pack(side="left", padx=(0,20))

        global total_time_val
        total_time_lbl = ctk.CTkLabel(stats_row, text="Total Time:", font=("Consolas", 12, "bold"))
        total_time_lbl.pack(side="left", padx=(0,5))
        total_time_val = ctk.CTkLabel(stats_row, text="00:00:00", font=("Consolas", 12))
        total_time_val.pack(side="left", padx=(0,20))

        global average_time_val
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

cambiar_contenido("Bot")

ventana.mainloop()
