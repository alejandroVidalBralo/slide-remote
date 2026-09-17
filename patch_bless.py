"""
Corrige un bug del paquete 'bless' 0.2.6 publicado en PyPI: importa un
paquete inexistente ('pysetupdi') de forma incondicional para una funcion
que no usamos (renombrar el adaptador Bluetooth del sistema). Este script
hace ese import perezoso para que bless funcione sin 'pysetupdi'.

Se ejecuta automaticamente desde setup.bat. Es idempotente: si ya esta
parcheado, no hace nada.
"""

import sys
import sysconfig
from pathlib import Path

# No usamos importlib.util.find_spec("bless...") a proposito: resolver un
# submodulo importa primero el paquete "bless", que es justo lo que falla
# sin este parche. Localizamos el archivo por ruta, sin importarlo.
site_packages = Path(sysconfig.get_paths()["purelib"])
path = site_packages / "bless" / "backends" / "winrt" / "server.py"

if not path.exists():
    print(f"No se encontro {path}; ¿se instalaron las dependencias?")
    sys.exit(1)
text = path.read_text(encoding="utf-8")

if "patched to import BLEAdapter lazily" in text:
    print("bless ya estaba parcheado, nada que hacer.")
    sys.exit(0)

text = text.replace(
    "from bless.backends.winrt.ble import BLEAdapter\n\n# CLR imports",
    "# NOTE: patched to import BLEAdapter lazily (see start()) because the\n"
    "# published bless 0.2.6 wheel depends on the unpublished \"pysetupdi\"\n"
    "# package, which breaks this import unconditionally on every server\n"
    "# construction even when adapter renaming (name_overwrite) is unused.\n\n"
    "# CLR imports",
)

text = text.replace(
    "self._adapter: BLEAdapter = BLEAdapter()",
    "self._adapter = None",
)

text = text.replace(
    "        if self._name_overwrite:\n            self._adapter.set_local_name(self.name)",
    "        if self._name_overwrite:\n"
    "            from bless.backends.winrt.ble import BLEAdapter\n\n"
    "            if self._adapter is None:\n"
    "                self._adapter = BLEAdapter()\n"
    "            self._adapter.set_local_name(self.name)",
)

# Windows a menudo no puede meter el nombre local Y el UUID de servicio de
# 128 bits en un solo paquete de anuncio (limite de 31 bytes), asi que el
# estado que devuelve es "StartedWithoutAllAdvertisementData" (3) en vez de
# "Started" (2). bless solo trata el 2 como exito y se queda esperando para
# siempre. Como filtramos por UUID de servicio (no por nombre), el estado 3
# nos vale igual.
text = text.replace(
    "                winrt_service.service_provider.advertisement_status == 2",
    "                winrt_service.service_provider.advertisement_status in (2, 3)",
)
text = text.replace(
    "        if args.status == 2:",
    "        if args.status in (2, 3):",
)

path.write_text(text, encoding="utf-8")
print("bless parcheado correctamente.")
