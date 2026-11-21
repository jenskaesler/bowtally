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
_USER_CHOICE_KEY = (r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations"
                    r"\whatsapp\UserChoice")


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


def whatsapp_link_assigned() -> bool:
    """The link type whatsapp:// opens an app: a default chosen in Windows (UserChoice) or a
    classic handler with an open command."""
    if not is_windows():
        return True
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _USER_CHOICE_KEY) as key:
            if winreg.QueryValueEx(key, "ProgId")[0]:
                return True
    except OSError:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"whatsapp\shell\open\command") as key:
            return bool(winreg.QueryValueEx(key, "")[0])
    except OSError:
        return False


def open_default_app_settings() -> bool:
    """Open Windows Settings > Default apps at WhatsApp Desktop (Windows 11), otherwise the
    general default apps page. Returns False when Settings could not be opened."""
    if not is_windows():
        return False
    if whatsapp_desktop_installed() and QDesktopServices.openUrl(
            QUrl(f"ms-settings:defaultapps?registeredAUMID={WHATSAPP_AUMID}")):
        return True
    return QDesktopServices.openUrl(QUrl("ms-settings:defaultapps"))
