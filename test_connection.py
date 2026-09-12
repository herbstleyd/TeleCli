#!/usr/bin/env python3
"""
Diagnose-Skript: Testet die Telegram-Verbindung ohne TUI.
Prüft Schritt für Schritt, wo das Problem liegt.
"""

import asyncio
import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "telecli"
SESSION_NAME = str(CONFIG_DIR / "session")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

API_ID = os.environ.get("TG_API_ID")
API_HASH = os.environ.get("TG_API_HASH")

if not API_ID or not API_HASH:
    print("FEHLER: TG_API_ID und TG_API_HASH nicht gesetzt!")
    sys.exit(1)

# Alte Session-Dateien löschen, um einen sauberen Start zu garantieren
for f in CONFIG_DIR.glob("session*"):
    print(f"Lösche alte Session-Datei: {f}")
    f.unlink()

from telethon import TelegramClient


async def test():
    print()
    print("=" * 50)
    print("Telecli — Verbindungsdiagnose")
    print("=" * 50)
    print()

    # Schritt 1: Client erstellen
    print("[1/5] Erstelle TelegramClient...")
    print(f"      API_ID: {API_ID}")
    print(f"      API_HASH: {API_HASH[:8]}...")
    print(f"      Session: {SESSION_NAME}")
    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    print("      OK")
    print()

    # Schritt 2: Verbinden
    print("[2/5] Verbinde mit Telegram-Servern...")
    try:
        await asyncio.wait_for(client.connect(), timeout=30.0)
        print("      Verbunden!")
    except asyncio.TimeoutError:
        print("      FEHLER: Timeout nach 30 Sekunden")
        print("      Mögliche Ursachen:")
        print("        - Keine Internetverbindung")
        print("        - Firewall blockiert Telegram-Server")
        print("        - DNS-Auflösung schlägt fehl")
        await client.disconnect()
        return
    except Exception as e:
        print(f"      FEHLER: {e}")
        await client.disconnect()
        return
    print()

    # Schritt 3: Autorisierung prüfen
    print("[3/5] Prüfe Login-Status...")
    try:
        authorized = await asyncio.wait_for(client.is_user_authorized(), timeout=15.0)
        print(f"      Eingeloggt: {'ja' if authorized else 'nein'}")
    except asyncio.TimeoutError:
        print("      FEHLER: Timeout bei Login-Prüfung")
        await client.disconnect()
        return
    except Exception as e:
        print(f"      FEHLER: {e}")
        await client.disconnect()
        return
    print()

    # Schritt 4: Falls nicht eingeloggt, Login durchführen
    if not authorized:
        print("[4/5] Login erforderlich")
        phone = input("      Telefonnummer (z.B. +49...): ").strip()
        print(f"      Sende Code an {phone}...")
        try:
            await client.send_code_request(phone)
            print("      Code gesendet!")
        except Exception as e:
            print(f"      FEHLER beim Senden des Codes: {e}")
            await client.disconnect()
            return

        code = input("      Bestätigungscode: ").strip()
        try:
            await client.sign_in(phone, code)
            print("      Login erfolgreich!")
        except Exception as e:
            print(f"      FEHLER beim Login: {e}")
            print(f"      (Falls 2FA aktiv: {e})")
            await client.disconnect()
            return
    else:
        print("[4/5] Bereits eingeloggt — überspringe Login")
    print()

    # Schritt 5: Benutzer abrufen
    print("[5/5] Lade Benutzerdaten...")
    try:
        me = await asyncio.wait_for(client.get_me(), timeout=15.0)
        print(f"      Eingeloggt als: {me.first_name} (ID: {me.id})")
        print()
        print("Diagnose erfolgreich! Die Verbindung zu Telegram funktioniert.")
        print("Das Problem liegt bei der Textual/TUI-Integration.")
    except Exception as e:
        print(f"      FEHLER: {e}")
    finally:
        await client.disconnect()

    print()
    print("Fertig.")


if __name__ == "__main__":
    asyncio.run(test())
