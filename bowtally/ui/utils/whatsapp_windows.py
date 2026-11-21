# -*- coding: utf-8 -*-
"""Windows: is the link type whatsapp:// assigned to an app, and open the Windows page to assign it.

wa.me hands over to WhatsApp Desktop via a whatsapp:// link. Windows protects default apps with a
hash (UserChoice), so no app may set the assignment itself; BowTally only reads the state and
opens Windows Settings at the default apps of WhatsApp Desktop, where the user assigns the link
type with one click.
"""
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

# WhatsApp Desktop from the Microsoft Store: the package family is the same on every PC
WHATSAPP_PACKAGE_FAMILY = "5319275A.WhatsAppDesktop_cv1g1gvanyjgm"
WHATSAPP_AUMID = WHATSAPP_PACKAGE_FAMILY + "!App"
_PACKAGES_KEY = (r"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion"
                 r"\AppModel\Repository\Packages")
ASSOCF_IS_PROTOCOL, ASSOCSTR_PROGID = 0x1000, 20         # shlwapi AssocQueryStringW


def is_windows() -> bool:
    return sys.platform == "win32"


def whatsapp_desktop_installed() -> bool:
    """WhatsApp Desktop (Store app) is installed for the current user."""
    if not is_windows():
        return False
    import winreg
    prefix = WHATSAPP_PACKAGE_FAMILY.split("_")[0] + "_"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PACKAGES_KEY) as key:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(key, i)
                except OSError:
                    return False
                if name.startswith(prefix) and name.endswith(WHATSAPP_PACKAGE_FAMILY.split("_")[1]):
                    return True
                i += 1
    except OSError:
        return False


def whatsapp_link_assigned(protocol: str = "whatsapp") -> bool:
    """The link type whatsapp:// opens an app. Asks Windows for the effective handler (the same
    lookup Explorer uses): Windows 11 keeps the choice outside the classic UserChoice key, and
    without a choice the ProgID is "Undecided"."""
    if not is_windows():
        return True
    import ctypes
    from ctypes import wintypes
    query = ctypes.windll.shlwapi.AssocQueryStringW
    query.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                      wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    size = wintypes.DWORD(512)
    buf = ctypes.create_unicode_buffer(size.value)
    ok = query(ASSOCF_IS_PROTOCOL, ASSOCSTR_PROGID, protocol, None, buf, ctypes.byref(size)) == 0
    return ok and buf.value not in ("", "Undecided")


def open_default_app_settings() -> bool:
    """Open Windows Settings > Default apps at WhatsApp Desktop (Windows 11), otherwise the
    general default apps page. Returns False when Settings could not be opened."""
    if not is_windows():
        return False
    if whatsapp_desktop_installed() and QDesktopServices.openUrl(
            QUrl(f"ms-settings:defaultapps?registeredAUMID={WHATSAPP_AUMID}")):
        return True
    return QDesktopServices.openUrl(QUrl("ms-settings:defaultapps"))
