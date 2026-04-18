#!/usr/bin/env python3
"""
tAplaudo — abre tus aplicaciones con dos palmadas.

Detecta 2 aplausos por el micrófono → saluda por voz → abre las URLs
y aplicaciones que hayas configurado en la sección CONFIGURACIÓN.

"""

import os
import sys
import time
import asyncio
import platform
import tempfile
import threading
import subprocess
import webbrowser
from typing import cast

import numpy as np
import sounddevice as sd
import pyttsx3


#  CONFIGURACIÓN  ←  edita aquí para personalizar tAplaudo

# Mensaje que dirá la voz al detectar los aplausos
MENSAJE = "Bienvenido a casa entreunosyceros."

# URLs que se abrirán en el navegador (añade o quita las que quieras)
URLS = [
    "https://www.youtube.com/@entreunosyceros",
    "https://www.instagram.com/entreunosyceros/",
    # "https://www.google.com",   # ← descomenta para añadir más URLs
]

# Aplicaciones que se lanzarán (nombre del ejecutable o ruta completa)
# En Linux usa el nombre del binario; en Windows la ruta al .exe
# Ejemplos:
#   "code"          → Visual Studio Code
#   "thunderbird"   → Mozilla Thunderbird (instalación nativa)
#   "firefox"       → Mozilla Firefox
#   ("flatpak", "run", "org.mozilla.Thunderbird")  → Thunderbird via Flatpak
APLICACIONES = [
    "code",         # Visual Studio Code
    "thunderbird",  # Mozilla Thunderbird
]

# Voz neuronal de edge-tts (requiere internet). Otras opciones:
#   "es-ES-AlvaroNeural"   → masculina (España)
#   "es-MX-DaliaNeural"    → femenina (México)
#   "es-AR-ElenaNeural"    → femenina (Argentina)
VOZ_EDGE = "es-ES-ElviraNeural"

#  Parámetros de detección de aplausos (ajusta si no detecta bien)
SAMPLE_RATE   = 44100
BLOCK_SIZE    = int(SAMPLE_RATE * 0.05)  # 50 ms por bloque
THRESHOLD     = 0.25   # RMS mínimo para contar como aplauso (sube si hay ruido)
COOLDOWN      = 0.2    # segundos mínimos entre palmadas (evita contar ecos del mismo aplauso)
DOUBLE_WINDOW = 3.0    # ventana máxima entre la 1ª y 2ª palmada (segundos)

#  Estado global
clap_times: list[float] = []
triggered = False
lock = threading.Lock()
done_event = threading.Event()


#  Detección de aplausos
def audio_callback(indata, frames, time_info, status):
    global triggered, clap_times

    if triggered:
        return

    rms = float(np.sqrt(np.mean(indata ** 2)))
    now = time.time()

    if rms > THRESHOLD:
        with lock:
            # Ignora si estamos en el cooldown del aplauso anterior
            if clap_times and (now - clap_times[-1]) < COOLDOWN:
                return

            clap_times.append(now)
            # Elimina en sitio los aplausos fuera de la ventana (sin reasignar la lista)
            while clap_times and (now - clap_times[0]) > DOUBLE_WINDOW:
                clap_times.pop(0)

            count = len(clap_times)
            print(f"  👏  Aplauso {count}/2  (RMS={rms:.3f})")

            if count >= 2:
                triggered = True
                clap_times = []
                threading.Thread(target=secuencia_bienvenida, daemon=True).start()


#  Secuencia de bienvenida
def secuencia_bienvenida():
    print("\n🚀  Iniciando secuencia de bienvenida…\n")

    hablar(MENSAJE)
    abrir_urls()
    abrir_aplicaciones()

    print("\n✅  Secuencia completada.\n")
    done_event.set()


def hablar(texto: str):
    """TTS: edge-tts (voz neural, requiere internet) con fallback a espeak/pyttsx3."""
    print(f"  \U0001f50a  Diciendo: \u00ab{texto}\u00bb")

    if platform.system().lower() != "windows":
        # ─ Intenta edge-tts (voz neuronal, la más natural) ───────────────────
        if _hablar_edge(texto):
            return
        # ─ Fallback: espeak-ng ──────────────────────────────────────────
        resultado = subprocess.run(
            ["espeak-ng", "-v", "es", "-s", "148", texto],
            capture_output=True
        )
        if resultado.returncode == 0:
            return

    # Windows (o último fallback)
    engine = pyttsx3.init()
    voices = cast(list, engine.getProperty("voices") or [])
    esp = [v for v in voices if "es" in v.id.lower() or "spanish" in v.name.lower()]
    if esp:
        engine.setProperty("voice", esp[0].id)
    engine.setProperty("rate", 148)
    engine.say(texto)
    engine.runAndWait()


def _hablar_edge(texto: str) -> bool:
    """Genera audio con edge-tts y lo reproduce. Devuelve True si tiene éxito."""
    tmp = ""
    try:
        import edge_tts  # type: ignore  # noqa: PLC0415

        tmp = tempfile.mktemp(suffix=".mp3")

        async def _generar():
            communicate = edge_tts.Communicate(texto, VOZ_EDGE)
            await communicate.save(tmp)

        asyncio.run(_generar())

        # Reproduce con el primer reproductor disponible
        for reproductor in [["mpv", "--no-video", tmp],
                            ["ffplay", "-nodisp", "-autoexit", tmp],
                            ["cvlc", "--play-and-exit", tmp]]:
            r = subprocess.run(reproductor, capture_output=True)
            if r.returncode == 0:
                return True

        return False
    except Exception:
        return False
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def abrir_urls():
    for url in URLS:
        print(f"  -> 🌐  Abriendo {url}…")
        webbrowser.open(url)
        time.sleep(1.0)


def abrir_aplicaciones():
    sistema = platform.system().lower()
    for app in APLICACIONES:
        # Permite entradas como ("flatpak", "run", "org.mozilla.Thunderbird")
        if isinstance(app, (list, tuple)):
            cmd = list(app)
        else:
            cmd = _resolver_ejecutable(app, sistema)

        print(f"  -> 🖥️  Abriendo {app if isinstance(app, str) else app[0]}…")
        if cmd:
            subprocess.Popen(cmd)
        else:
            print(f"     [!] No se encontró: {app}")
        time.sleep(1.0)


def _resolver_ejecutable(nombre: str, sistema: str):
    """Busca el ejecutable de una app: rutas conocidas, Flatpak y PATH."""
    # Rutas estándar por plataforma
    rutas = {
        "windows": {
            "code": [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\bin\code.cmd"),
            ],
            "thunderbird": [
                os.path.expandvars(r"%ProgramFiles%\Mozilla Thunderbird\thunderbird.exe"),
                os.path.expandvars(r"%ProgramW6432%\Mozilla Thunderbird\thunderbird.exe"),
            ],
        },
        "linux": {
            "code": ["/usr/bin/code", "/usr/local/bin/code", "/snap/bin/code",
                     os.path.expanduser("~/.local/bin/code")],
            "thunderbird": ["/usr/bin/thunderbird", "/usr/local/bin/thunderbird",
                            "/snap/bin/thunderbird",
                            os.path.expanduser("~/.local/bin/thunderbird")],
        },
    }

    plataforma = "windows" if sistema == "windows" else "linux"
    for ruta in rutas.get(plataforma, {}).get(nombre, []):
        if os.path.isfile(ruta):
            return [ruta]

    # Flatpak (Linux): busca por nombre de app conocido
    flatpak_ids = {
        "thunderbird": "org.mozilla.Thunderbird",
        "code":        "com.visualstudio.code",
    }
    if sistema != "windows" and nombre in flatpak_ids:
        result = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and flatpak_ids[nombre] in result.stdout:
            return ["flatpak", "run", "--no-sandbox", flatpak_ids[nombre]]

    # Fallback: PATH del sistema
    result = subprocess.run(
        ["where" if sistema == "windows" else "which", nombre],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return [result.stdout.strip().splitlines()[0]]

    return None


#  Main
def main():
    global triggered

    print()
    print("=" * 55)
    print("  🎤  En pausa. Aplaude dos veces para comenzar.")
    print(f"  (Umbral RMS: {THRESHOLD} — ajusta THRESHOLD si no detecta)")
    print("  Ctrl+C para salir")
    print("=" * 55)
    print()

    try:
        print("  Calibrando micrófono…")
        time.sleep(1.5)  # pausa para que el mic se estabilice antes de escuchar
        print("  ¡Listo! Esperando palmadas…\n")
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=1,
            dtype="float32",
            callback=audio_callback,
        ):
            while not done_event.is_set():
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n👋👋")
        sys.exit(0)


if __name__ == "__main__":
    main()
