"""
Mando a distancia para diapositivas via Bluetooth Low Energy, con puntero
laser virtual.

El PC se anuncia como periferico BLE ("SlideRemote-PC"). El movil se conecta
desde el navegador (Chrome Android, Web Bluetooth) usando remote.html y envia
comandos que aqui se traducen en pulsaciones de teclado reales, o en el
movimiento de un punto rojo superpuesto a la pantalla (el "laser").

Requisitos: Windows 10/11 con Bluetooth LE, Python 3.9+.
Instalar dependencias:  pip install -r requirements.txt
Ejecutar:               python server.py
"""

import asyncio
import logging
import queue
import sys
import threading
import time
import tkinter as tk
from collections import deque

import pyautogui
import win32con
import win32gui
from bless import (
    BlessGATTCharacteristic,
    BlessServer,
    GATTAttributePermissions,
    GATTCharacteristicProperties,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("slide-remote")

# Mismos UUID que en remote.html - no cambiar uno sin el otro.
SERVICE_UUID = "bc6a428d-134f-48d0-b097-5ee6c4a89ba9"
CHAR_UUID = "1c2d9c03-ae5b-4dad-b9c9-8236b88b5f70"

KEY_COMMANDS = {
    0x01: ("right", "-> Siguiente diapositiva"),
    0x02: ("left", "<- Diapositiva anterior"),
    0x03: ("f5", ">> Iniciar presentacion (PowerPoint)"),
    0x04: ("esc", "x  Salir de pantalla completa"),
    0x05: ("b", "## Pantalla negra"),
    0x06: ("w", "## Pantalla blanca"),
    0x14: ("space", "|| Play/Pause"),
    0x31: ("backspace", "<- Borrar"),
    0x32: ("enter", "Intro"),
    0x33: ("tab", "Tab"),
    0x38: ("up", "Flecha arriba"),
    0x39: ("down", "Flecha abajo"),
}
# Combinacion de teclas (no una sola tecla), asi que va aparte de KEY_COMMANDS.
START_BROWSER = 0x13
START_BROWSER_HOTKEY = ("ctrl", "shift", "f5")
GOTO_SLIDE = 0x07
LASER_MOVE = 0x10
LASER_SHOW = 0x11
LASER_HIDE = 0x12
MOUSE_MOVE = 0x20
MOUSE_LEFT_CLICK = 0x21
MOUSE_RIGHT_CLICK = 0x22
TYPE_CHAR = 0x30

MOUSE_SENSITIVITY = 1.6

pyautogui.FAILSAFE = False
# pyautogui pausa 0.1s tras CADA llamada por defecto; con el raton y el
# teclado remotos eso se nota muchisimo (movimientos a tirones, tecleo con
# retraso), asi que lo desactivamos.
pyautogui.PAUSE = 0

# Cola thread-safe: el callback BLE llega en el hilo del servidor asincrono,
# pero solo el hilo principal (donde vive tkinter) puede tocar la ventana.
pointer_queue: "queue.Queue" = queue.Queue()


class LaserOverlay:
    """Ventanita transparente y clic-transparente que se recentra sobre el
    dedo: dibuja un punto rojo redondo con una estela que se disipa.

    Nota: se probo primero con una capa cubriendo toda la pantalla, pero el
    truco de "-transparentcolor" de Windows deja de funcionar de forma
    fiable en una ventana a pantalla completa (se ve todo en negro). Una
    ventana pequena que sigue al dedo (como la version original sin
    estela) si funciona, y es suficiente para contener el rastro reciente.
    """

    WIN_SIZE = 240
    HALF = WIN_SIZE // 2
    DOT_RADIUS = 9
    TRAIL_MIN_RADIUS = 2
    TRAIL_MS = 260  # cuanto tarda la estela en disiparse por completo
    TICK_MS = 25  # ~40 fps

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg="black")
        self.root.attributes("-transparentcolor", "black")
        self.root.geometry(f"{self.WIN_SIZE}x{self.WIN_SIZE}+0+0")

        self.canvas = tk.Canvas(
            self.root,
            width=self.WIN_SIZE,
            height=self.WIN_SIZE,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.root.update_idletasks()
        self._make_click_through()

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        self.visible = False
        self.pos: "tuple[float, float] | None" = None
        self.trail: "deque[tuple[float, float, float]]" = deque()

        self.root.withdraw()
        self.root.after(15, self._poll_queue)
        self.root.after(self.TICK_MS, self._render)

    def _make_click_through(self) -> None:
        hwnd = self.root.winfo_id()
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            styles | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT,
        )
        # Tocar GWL_EXSTYLE borra la clave de color que puso "-transparentcolor"
        # (Windows vuelve a pintar la ventana en negro solido). Hay que
        # reaplicarla o se ve un cuadrado negro enorme en vez de transparente.
        win32gui.SetLayeredWindowAttributes(hwnd, 0x000000, 0, win32con.LWA_COLORKEY)

    def _poll_queue(self) -> None:
        try:
            while True:
                self._handle(pointer_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(15, self._poll_queue)

    def _handle(self, msg) -> None:
        kind = msg[0]
        if kind == "move":
            _, nx, ny = msg
            x = nx * self.screen_w
            y = ny * self.screen_h
            self.pos = (x, y)
            self.trail.append((x, y, time.monotonic()))
        elif kind == "show":
            self.visible = True
            self.root.deiconify()
        elif kind == "hide":
            self.visible = False
            self.pos = None
            self.trail.clear()
            self.canvas.delete("all")
            self.root.withdraw()

    def _render(self) -> None:
        if self.visible and self.pos:
            px, py = self.pos
            left = int(px) - self.HALF
            top = int(py) - self.HALF
            self.root.geometry(f"+{left}+{top}")

            self.canvas.delete("all")
            now = time.monotonic()
            while self.trail and (now - self.trail[0][2]) * 1000 > self.TRAIL_MS:
                self.trail.popleft()

            for x, y, created in self.trail:
                fade = 1.0 - min(1.0, (now - created) * 1000 / self.TRAIL_MS)
                color = f"#{int(255 * fade):02x}{int(40 * fade):02x}{int(40 * fade):02x}"
                radius = self.TRAIL_MIN_RADIUS + (self.DOT_RADIUS - self.TRAIL_MIN_RADIUS) * fade
                lx, ly = x - left, y - top
                self.canvas.create_oval(
                    lx - radius, ly - radius, lx + radius, ly + radius, fill=color, outline=""
                )

            r = self.DOT_RADIUS
            lx, ly = px - left, py - top
            self.canvas.create_oval(
                lx - r, ly - r, lx + r, ly + r, fill="#ff2828", outline="#ffdede", width=1
            )

        self.root.after(self.TICK_MS, self._render)

    def run(self) -> None:
        self.root.mainloop()


def read_request(characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
    return characteristic.value


def _to_signed_byte(b: int) -> int:
    return b - 256 if b > 127 else b


def write_request(characteristic: BlessGATTCharacteristic, value, **kwargs) -> None:
    characteristic.value = value
    if not value:
        return
    code = value[0]

    if code in KEY_COMMANDS:
        key, label = KEY_COMMANDS[code]
        logger.info(label)
        pyautogui.press(key)
    elif code == START_BROWSER:
        logger.info(">> Iniciar presentacion (navegador)")
        pyautogui.hotkey(*START_BROWSER_HOTKEY)
    elif code == GOTO_SLIDE and len(value) >= 3:
        n = int.from_bytes(value[1:3], "big")
        logger.info("-> Ir a diapositiva %d", n)
        pyautogui.typewrite(str(n))
        pyautogui.press("enter")
    elif code == LASER_MOVE and len(value) >= 5:
        nx = int.from_bytes(value[1:3], "big") / 65535
        ny = int.from_bytes(value[3:5], "big") / 65535
        pointer_queue.put(("move", nx, ny))
    elif code == LASER_SHOW:
        pointer_queue.put(("show",))
    elif code == LASER_HIDE:
        pointer_queue.put(("hide",))
    elif code == MOUSE_MOVE and len(value) >= 3:
        dx = _to_signed_byte(value[1])
        dy = _to_signed_byte(value[2])
        pyautogui.moveRel(round(dx * MOUSE_SENSITIVITY), round(dy * MOUSE_SENSITIVITY))
    elif code == MOUSE_LEFT_CLICK:
        pyautogui.click()
    elif code == MOUSE_RIGHT_CLICK:
        pyautogui.click(button="right")
    elif code == TYPE_CHAR and len(value) >= 2:
        try:
            text = bytes(value[1:]).decode("utf-8")
            pyautogui.typewrite(text)
        except Exception as exc:  # caracter no tecleable, no es fatal
            logger.warning("No se pudo escribir el caracter %r: %s", value[1:], exc)
    else:
        logger.warning("Comando desconocido: %r", value)


async def run_ble_server() -> None:
    server = BlessServer(name="SlideRemote-PC")
    server.read_request_func = read_request
    server.write_request_func = write_request

    await server.add_new_service(SERVICE_UUID)

    char_flags = (
        GATTCharacteristicProperties.write
        | GATTCharacteristicProperties.write_without_response
        | GATTCharacteristicProperties.read
    )
    permissions = GATTAttributePermissions.writeable | GATTAttributePermissions.readable
    await server.add_new_characteristic(
        SERVICE_UUID, CHAR_UUID, char_flags, bytearray(b"\x00"), permissions
    )

    await server.start()
    print("=" * 60)
    print(" Servidor Bluetooth activo como 'SlideRemote-PC'")
    print(" En el movil: abre remote.html en Chrome y pulsa Conectar")
    print(" Cierra esta ventana para detener el servidor")
    print("=" * 60)

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await server.stop()
        print("Servidor detenido.")


def run_overlay_thread() -> None:
    # tkinter (y su mainloop) viven enteramente en este hilo; el hilo
    # principal corre el servidor BLE via WinRT, que es donde ya sabemos
    # que funciona de forma fiable.
    overlay = LaserOverlay()
    overlay.run()


def main() -> None:
    thread = threading.Thread(target=run_overlay_thread, daemon=True)
    thread.start()
    asyncio.run(run_ble_server())


if __name__ == "__main__":
    if sys.platform != "win32":
        logger.warning("Este script se ha probado en Windows; en otros SO puede variar.")
    main()
