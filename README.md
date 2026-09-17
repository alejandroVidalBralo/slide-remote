# Bluepointer

Convierte tu Windows en un mando de presentaciones controlado desde el navegador del móvil, por Bluetooth Low Energy — sin instalar ninguna app en el móvil y sin necesitar la misma red WiFi.

- **Anterior / siguiente diapositiva**, iniciar presentación (PowerPoint o navegador), pantalla negra/blanca, ir a una diapositiva concreta, play/pause.
- **Puntero láser virtual**: un punto rojo con estela que sigue tu dedo, superpuesto a cualquier ventana.
- **Ratón y teclado táctiles**: controla el cursor real del PC y escribe texto desde el móvil.

## Cómo funciona

El PC se anuncia como un periférico BLE (usando [`bless`](https://github.com/kevincar/bless), sobre la API WinRT de Windows). El móvil se conecta directamente por Bluetooth desde una página web normal usando la [Web Bluetooth API](https://developer.chrome.com/docs/capabilities/bluetooth) de Chrome — sin apps nativas, sin necesitar la misma red, sin servidor intermedio. Solo hace falta Bluetooth encendido en ambos dispositivos.

```
Movil (Chrome, Web Bluetooth)  <--BLE-->  PC (bless: periferico GATT)
     index.html                                server.py
                                                   |
                                          pyautogui (teclas, raton)
```

Esta combinación —PC como *periférico* BLE controlado desde un navegador sin app— no es la forma habitual de resolver esto (lo normal es WiFi + servidor HTTP, o un dongle/mando físico), así que este proyecto nació de necesitar un mando que funcionase en una red donde el móvil y el PC están en subredes distintas (por ejemplo, WiFi de universidad).

## Requisitos

- **PC con Windows 10/11** con Bluetooth LE (cualquier adaptador de la última década vale) y Python 3.11 (`bless` no es compatible con versiones más nuevas de Python en Windows — ver `requirements.txt`).
- **Móvil Android con Google Chrome.** Safari/iPhone no soporta Web Bluetooth, así que no es compatible con iPhone.

## Instalación

```bat
setup.bat
```

Crea un entorno virtual con Python 3.11, instala las dependencias y aplica un parche necesario a `bless` (ver `patch_bless.py` — corrige un par de bugs del paquete publicado en PyPI: una dependencia inexistente, y un estado de "anuncio BLE iniciado" que Windows devuelve a veces y que la librería no reconocía).

## Uso

1. Doble clic en `start.bat` (o en el acceso directo del escritorio, si lo has creado).
2. En el móvil, abre la página publicada de este repo (GitHub Pages) en Chrome — o `index.html` directamente.
3. Pulsa **Conectar** y elige el PC en la lista.

## Estructura

| Archivo | Qué es |
|---|---|
| `server.py` | El servidor BLE + simulador de teclado/ratón + overlay del láser. Se ejecuta en el PC. |
| `index.html` | La página que se abre en el móvil. Publicada vía GitHub Pages. |
| `patch_bless.py` | Corrige bugs del paquete `bless` de PyPI. Se ejecuta automáticamente desde `setup.bat`. |
| `setup.bat` / `start.bat` | Instalación y arranque de doble clic. |
| `make_icon.py` | Genera `icon.ico` para un acceso directo con icono propio en el escritorio. |

## Limitaciones conocidas

- Solo Android + Chrome (Web Bluetooth no existe en Safari/iOS).
- El alcance es el de Bluetooth LE (unos 10 metros en interiores).
- No hay (ni puede haber de forma razonable) espejo de la pantalla del PC en el móvil: BLE no tiene ancho de banda para vídeo.

## Licencia

MIT — usa, copia y modifica libremente.
