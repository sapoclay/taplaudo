# 👏 tAplaudo 👏

<img width="1408" height="768" alt="tAplaudo" src="https://github.com/user-attachments/assets/8c41fbea-541e-42fc-971c-fbcbc0640dd1" />

Aplaude dos veces y tu ordenador te da la bienvenida: una voz pronuncia tu mensaje, se abren las URLs que quieras en el navegador y se lanzan las aplicaciones que hayas configurado.

Funciona en **Linux** y **Windows**.

> [!NOTE]
> Esta idea la tomé prestada de otro código que encontré en https://github.com/RafaTatay/jarvis ... y que a su vez creo que este hombre la sacó de otro sitio. La idea creo que me puede venir bien para desarrollar algo para Kodi ... si tengo tiempo. Por el momento la adapté a mi equipo principal.

---

## ¿Qué hace?

1. Escucha el micrófono en segundo plano.
2. Al detectar **2 palmadas** en menos de 2 segundos, inicia la secuencia:
   - Una voz dice el mensaje de bienvenida configurado.
   - Abre las URLs indicadas en el navegador por defecto.
   - Lanza las aplicaciones de escritorio configuradas.
3. El programa termina tras completar la secuencia.

---

## Requisitos

- Python 3.10 o superior
- Micrófono
- Conexión a internet (para la voz neuronal de `edge-tts`)
- En Linux, un reproductor de audio: `mpv`, `ffplay` o `vlc`

```bash
# Instalar mpv en Ubuntu/Debian si no está disponible
sudo apt install mpv
```

---

## Instalación y ejecución

```bash
# Clona o descarga el proyecto y entra en la carpeta
cd tAplaudo

# Ejecuta el lanzador (crea el entorno virtual e instala dependencias solo la primera vez)
python run_app.py
```

> En Windows usa `python run_app.py` desde el Símbolo del sistema o PowerShell.

---

## Configuración

Abre **`bienvenido.py`** y edita la sección `CONFIGURACIÓN` al principio del archivo:

```python
# Mensaje que dirá la voz al detectar los aplausos
MENSAJE = "Bienvenido a casa entreunosyceros."

# URLs que se abrirán en el navegador (añade o quita las que quieras)
URLS = [
    "https://www.youtube.com/@entreunosyceros",
    # "https://www.google.com",
]

# Aplicaciones que se lanzarán (nombre del ejecutable o ruta completa)
APLICACIONES = [
    "code",         # Visual Studio Code
    "thunderbird",  # Mozilla Thunderbird
    # "firefox",
    # "spotify",
]

# Voz neuronal (edge-tts). Más voces en español:
#   "es-ES-AlvaroNeural"  → masculina (España)
#   "es-MX-DaliaNeural"   → femenina (México)
#   "es-AR-ElenaNeural"   → femenina (Argentina)
VOZ_EDGE = "es-ES-ElviraNeural"
```

### Añadir una aplicación instalada como Flatpak

```python
APLICACIONES = [
    ("flatpak", "run", "--no-sandbox", "org.mozilla.Thunderbird"),
]
```

### Ajustar la sensibilidad del micrófono

Si los aplausos no se detectan (o se detectan con demasiado ruido), ajusta `THRESHOLD` en la sección de parámetros:

```python
THRESHOLD = 0.25   # Sube el valor si hay ruido ambiental
                   # Baja el valor si no detecta los aplausos
```

---

## Estructura del proyecto

```
tAplaudo/
├── run_app.py       # Lanzador: crea el entorno virtual y arranca bienvenido.py
├── bienvenido.py    # Programa principal (detección + secuencia de bienvenida)
└── requirements.txt # Dependencias Python
```
