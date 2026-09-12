#!/usr/bin/env python3
"""
Telecli — Terminal-basierter Telegram-Client
Layout der originalen App: Chatliste links, Nachrichten rechts, Eingabe unten.
Navigation mit Pfeiltasten. Farben für farbige Konsolen.

Features:
  - Textnachrichten senden/empfangen
  - Medien-Upload:   /upload /pfad/zur/datei [Caption]
  - Medien-Download: /download [Nr]
  - Medienliste:     /media
  - Hilfe:           /help

Abhängigkeiten: telethon, textual
Installation: pip install -r requirements.txt

API-Daten erforderlich: TG_API_ID und TG_API_HASH als Umgebungsvariablen.
Siehe README.md für Anleitung.
"""

import asyncio
import os
import sys
import shlex
import datetime
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import User, Chat, Channel

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import ListView, ListItem, Label, Input, RichLog
from textual.reactive import reactive
from textual import on
from textual.message import Message

# --- Konfiguration ---
CONFIG_DIR = Path.home() / ".config" / "telecli"
SESSION_NAME = str(CONFIG_DIR / "session")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_DIR = Path(os.environ.get("TG_DOWNLOAD_DIR", str(Path.home() / "Downloads" / "telecli")))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

API_ID = os.environ.get("TG_API_ID")
API_HASH = os.environ.get("TG_API_HASH")


def check_api_credentials():
    """Prüft, ob API-ID und -Hash gesetzt sind."""
    if not API_ID or not API_HASH:
        print("=" * 60)
        print("FEHLER: TG_API_ID und TG_API_HASH sind nicht gesetzt!")
        print("=" * 60)
        print()
        print("So erhältst du deine API-Daten:")
        print("  1. Gehe zu https://my.telegram.org")
        print("  2. Melde dich mit deiner Telefonnummer an")
        print("  3. Klicke auf 'API development tools'")
        print("  4. Erstelle eine App (beliebiger Name)")
        print("  5. Kopiere api_id und api_hash")
        print()
        print("Setze sie als Umgebungsvariablen:")
        print("  export TG_API_ID='deine_api_id'")
        print("  export TG_API_HASH='dein_api_hash'")
        print()
        print("Oder trage sie in ~/.config/telecli/.env ein und")
        print("verwende das start.sh Skript.")
        sys.exit(1)


# --- Hilfsfunktionen ---
def display_name(entity):
    """Gibt den Anzeigenamen eines Chats/Benutzers zurück."""
    if entity is None:
        return "Unbekannt"
    if hasattr(entity, "title") and entity.title:
        return entity.title
    if hasattr(entity, "first_name"):
        name = entity.first_name or ""
        if hasattr(entity, "last_name") and entity.last_name:
            name += f" {entity.last_name}"
        return name.strip() or "Unbekannt"
    return str(getattr(entity, "id", "Unbekannt"))


def entity_icon(entity):
    """Gibt ein Icon für den Chat-Typ zurück."""
    if isinstance(entity, User):
        return "👤"
    if isinstance(entity, Channel):
        return "📢"
    if isinstance(entity, Chat):
        return "👥"
    return "💬"


def format_timestamp(dt):
    """Formatiert einen Zeitstempel."""
    if dt is None:
        return ""
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%H:%M")
    return ""


def truncate(text, max_len):
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def format_file_size(size_bytes):
    """Formatiert eine Dateigröße in eine lesbare Form."""
    if size_bytes is None or size_bytes <= 0:
        return "?"
    units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024.0:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def media_icon(message):
    """Gibt ein Icon für den Medientyp einer Nachricht zurück."""
    if message.sticker:
        return "🏷️"
    if message.voice:
        return "🎤"
    if message.video or message.gif:
        return "🎬"
    if message.photo:
        return "🖼️"
    if message.document:
        return "📎"
    if message.media:
        return "📦"
    return None


def media_description(message):
    """Gibt eine kurze Beschreibung des Mediums zurück."""
    icon = media_icon(message) or "📎"

    # Dateiname ermitteln
    name = None
    if hasattr(message, "file") and message.file:
        name = message.file.name

    if not name:
        if message.photo:
            name = "photo.jpg"
        elif message.sticker:
            name = "sticker"
        elif message.voice:
            name = "voice.ogg"
        elif message.video:
            name = "video.mp4"
        elif message.gif:
            name = "gif.mp4"
        else:
            name = "medien"

    size = None
    if hasattr(message, "file") and message.file:
        size = message.file.size

    size_str = format_file_size(size) if size else ""

    desc = f"{icon} {name}"
    if size_str:
        desc += f" ({size_str})"
    return desc


def has_media(message):
    """Prüft, ob eine Nachricht Medien enthält."""
    return message.media is not None and not (
        hasattr(message.media, "webpage") and message.media.webpage
    )


# --- Login (außerhalb des TUI, im Plain Terminal) ---
def do_login(client):
    """Führt den Login im Terminal durch (nicht im TUI)."""

    async def _login():
        await client.connect()
        if not await client.is_user_authorized():
            print("Telegram-Login erforderlich")
            print("=" * 50)
            phone = input("Telefonnummer (mit Ländervorwahl, z.B. +49...): ").strip()
            await client.send_code_request(phone)
            code = input("Bestätigungscode: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Zwei-Faktor-Passwort: ").strip()
                await client.sign_in(password=password)
            print("\nLogin erfolgreich!\n")
        else:
            print("Session gefunden.\n")

    # Eigene temporäre Event-Loop für den Login
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_login())
    finally:
        # Client trennen — wird später in Textuals Loop neu verbunden
        loop.run_until_complete(client.disconnect())
        loop.close()


# --- TUI Application ---
class TelecliApp(App):
    """Hauptanwendung für Telecli."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #chat-panel {
        width: 1fr;
        border: solid $primary;
        border-title: "Chats";
        background: $surface;
    }

    #message-panel {
        width: 2fr;
        border: solid $accent;
        border-title: "Nachrichten";
        background: $panel;
    }

    #chat-list {
        height: 1fr;
    }

    #chat-list > ListItem {
        padding: 0 1;
    }

    #chat-list > ListItem:hover {
        background: $boost;
    }

    #message-log {
        height: 1fr;
        border: none;
        padding: 0 1;
    }

    #input-panel {
        height: 3;
        dock: bottom;
        border: solid $primary;
        border-title: "Nachricht senden (/help für Hilfe)";
        background: $surface;
    }

    #message-input {
        height: 1fr;
    }

    #status-bar {
        height: 1;
        dock: bottom;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Beenden"),
        ("ctrl+r", "refresh", "Aktualisieren"),
        ("ctrl+l", "focus_chats", "Chats"),
        ("ctrl+i", "focus_input", "Eingabe"),
        ("ctrl+u", "upload", "Upload"),
        ("ctrl+d", "download_last", "Download"),
    ]

    current_chat = reactive(None)

    class ChatLoaded(Message):
        pass

    def __init__(self, api_id: int, api_hash: str):
        super().__init__()
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = None
        self._me = None
        self._messages = []          # Nachrichten des aktuellen Chats (chronologisch, älteste zuerst)
        self._media_map = {}         # display_nr -> message (für /download)
        self._next_display_nr = 1    # Zähler für Medien-Nummern
        self._progress_text = ""     # Aktueller Progress-Text für Statusleiste

    async def on_mount(self) -> None:
        """Wird beim Start der App aufgerufen — jetzt auf Textuals Event-Loop."""
        self.client = TelegramClient(SESSION_NAME, self.api_id, self.api_hash)
        await self.client.connect()

        # Prüfen ob Session gültig ist
        if not await self.client.is_user_authorized():
            # Session existiert nicht oder ist ungültig
            self.query_one("#message-log", RichLog).write(
                "[bold red]Keine gültige Session![/]\n"
                "Bitte zuerst mit Login anmelden (starte das Skript neu)."
            )
            return

        self._me = await self.client.get_me()
        await self.load_dialogs()

        # Event-Handler für eingehende Nachrichten
        @self.client.on(events.NewMessage(incoming=True))
        async def _on_new_message(event):
            await self.load_dialogs()
            if self.current_chat and event.chat_id == self.current_chat.id:
                await self.append_message_to_log(event.message)

    async def load_dialogs(self) -> None:
        """Lädt die Chatliste von Telegram."""
        if not self.client:
            return

        dialogs = await self.client.get_dialogs(limit=100)
        chat_list = self.query_one("#chat-list", ListView)
        chat_list.clear()

        for dialog in dialogs:
            name = display_name(dialog.entity)
            icon = entity_icon(dialog.entity)
            preview = ""
            if dialog.message and dialog.message.text:
                preview = truncate(dialog.message.text, 25)
            elif dialog.message and has_media(dialog.message):
                preview = media_description(dialog.message)
            elif dialog.message:
                preview = "[?]"
            time_str = format_timestamp(dialog.date)

            label_text = f"{icon} {name}\n   {truncate(preview, 30)}  {time_str}"
            item = ListItem(Label(label_text))
            item.dialog = dialog
            chat_list.append(item)

        self._update_status_bar()

    async def compose(self) -> ComposeResult:
        """Baut das Layout auf."""
        with Horizontal(id="main-container"):
            with Vertical(id="chat-panel"):
                yield ListView(id="chat-list")
            with Vertical(id="message-panel"):
                yield RichLog(id="message-log", markup=True)
        with Vertical(id="input-panel"):
            yield Input(id="message-input", placeholder="Nachricht schreiben... (/help für Hilfe)")
        yield Label(id="status-bar", markup=True)

    async def on_ready(self) -> None:
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """Aktualisiert die Statusleiste."""
        status = self.query_one("#status-bar", Label)
        me_name = display_name(self._me) if self._me else "?"
        chat_name = display_name(self.current_chat.entity) if self.current_chat else "Kein Chat"
        progress = f" | {self._progress_text}" if self._progress_text else ""
        status.update(f" Eingeloggt als: {me_name} | Chat: {chat_name}{progress}")

    def _set_progress(self, text: str):
        """Setzt den Progress-Text in der Statusleiste."""
        self._progress_text = text
        self._update_status_bar()

    @on(ListView.Selected, "#chat-list")
    async def on_chat_selected(self, event: ListView.Selected) -> None:
        """Wird aufgerufen, wenn ein Chat in der Liste ausgewählt wird."""
        item = event.item
        if hasattr(item, "dialog"):
            self.current_chat = item.dialog
            self._update_status_bar()
            await self.load_messages(item.dialog)

    async def load_messages(self, dialog) -> None:
        """Lädt die Nachrichten eines Chats."""
        log = self.query_one("#message-log", RichLog)
        log.clear()
        log.write(f"[bold]=== {display_name(dialog.entity)} ===[/]\n")

        # Nachrichten-Tracking zurücksetzen
        self._messages = []
        self._media_map = {}
        self._next_display_nr = 1

        messages = await self.client.get_messages(dialog.entity, limit=100)
        for msg in reversed(messages):
            await self.append_message_to_log(msg)

    async def append_message_to_log(self, message) -> None:
        """Fügt eine Nachricht zum Nachrichten-Log hinzu."""
        log = self.query_one("#message-log", RichLog)

        sender = None
        if message.sender_id:
            try:
                sender = await self.client.get_entity(message.sender_id)
            except Exception:
                pass
        sender_name = display_name(sender) if sender else "Unbekannt"
        time_str = format_timestamp(message.date)

        is_me = message.sender_id == self._me.id if self._me else False

        # Nachricht verfolgen
        self._messages.append(message)

        # Farbe für Absender
        if is_me:
            prefix = f"[bold cyan]▸ {sender_name}[/]"
        else:
            prefix = f"[bold yellow]◂ {sender_name}[/]"

        log.write(f"{prefix} [dim]({time_str})[/]")

        # Text anzeigen
        if message.text:
            log.write(f"  {message.text}")

        # Medien anzeigen
        if has_media(message):
            nr = self._next_display_nr
            self._next_display_nr += 1
            self._media_map[nr] = message

            desc = media_description(message)
            log.write(f"  [bold green]  [{nr}][/bold green] {desc} [dim]— /download {nr}[/]")

        log.write("")

    # --- Befehlsverarbeitung ---
    @on(Input.Submitted, "#message-input")
    async def on_message_submitted(self, event: Input.Submitted) -> None:
        """Wird aufgerufen, wenn die Eingabe bestätigt wird."""
        raw = event.value.strip()
        if not raw:
            return

        event.input.value = ""

        # Befehle erkennen
        if raw.startswith("/"):
            await self._handle_command(raw)
        else:
            if not self.current_chat:
                return
            await self._send_text(raw)

    async def _send_text(self, text: str):
        """Sendet eine Textnachricht und zeigt sie im Log."""
        await self.client.send_message(self.current_chat.entity, text)

        log = self.query_one("#message-log", RichLog)
        now = datetime.datetime.now()
        me_name = display_name(self._me) if self._me else "Ich"
        log.write(f"[bold cyan]▸ {me_name}[/] [dim]({now.strftime('%H:%M')})[/]")
        log.write(f"  {text}")
        log.write("")

        await self.load_dialogs()

    async def _handle_command(self, raw: str):
        """Verarbeitet Slash-Befehle."""
        log = self.query_one("#message-log", RichLog)

        try:
            parts = shlex.split(raw)
        except ValueError as e:
            log.write(f"[bold red]Fehler beim Parsen:[/] {e}")
            log.write("")
            return

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "/help":
            log.write("[bold]=== Befehle ===[/]")
            log.write("  [green]/upload[/] <pfad> [caption]  Datei/Bild senden")
            log.write("  [green]/download[/] [nr]           Medium herunterladen")
            log.write("  [green]/media[/]                   Medien in diesem Chat auflisten")
            log.write("  [green]/refresh[/]                 Chatliste aktualisieren")
            log.write("  [green]/help[/]                    Diese Hilfe")
            log.write("  [green]/quit[/]                    Beenden")
            log.write("")
            log.write("[dim]Tasten: Ctrl+U=Upload, Ctrl+D=Download, Ctrl+R=Aktualisieren[/]")
            log.write("")

        elif cmd == "/quit":
            self.exit()

        elif cmd == "/refresh":
            await self.load_dialogs()
            if self.current_chat:
                await self.load_messages(self.current_chat)

        elif cmd == "/upload":
            if not self.current_chat:
                log.write("[bold red]Kein Chat ausgewählt![/]")
                log.write("")
                return
            await self._handle_upload(args)

        elif cmd == "/download":
            if not self.current_chat:
                log.write("[bold red]Kein Chat ausgewählt![/]")
                log.write("")
                return
            await self._handle_download(args)

        elif cmd == "/media":
            await self._list_media()

        else:
            log.write(f"[bold red]Unbekannter Befehl:[/] {cmd}")
            log.write("[dim]/help für verfügbare Befehle[/]")
            log.write("")

    async def _handle_upload(self, args):
        """Lädt eine Datei hoch."""
        log = self.query_one("#message-log", RichLog)

        if not args:
            log.write("[bold red]Verwendung:[/] /upload <pfad> [caption]")
            log.write("[dim]Beispiel: /upload ~/Bilder/foto.jpg Schönes Bild[/]")
            log.write("")
            return

        file_path = os.path.expanduser(args[0])
        caption = " ".join(args[1:]) if len(args) > 1 else ""

        if not os.path.exists(file_path):
            log.write(f"[bold red]Datei nicht gefunden:[/] {file_path}")
            log.write("")
            return

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        log.write(f"[bold]Upload:[/] {file_name} ({format_file_size(file_size)})...")
        log.write("")

        # Progress-Callback
        last_percent = [-1]

        def progress_callback(sent, total):
            if total > 0:
                percent = int(sent / total * 100)
                # Nur bei 5%-Schritten aktualisieren
                if percent >= last_percent[0] + 5 or percent >= 100:
                    last_percent[0] = percent
                    self._set_progress(f"Upload: {percent}% ({format_file_size(sent)}/{format_file_size(total)})")

        try:
            await self.client.send_file(
                self.current_chat.entity,
                file_path,
                caption=caption if caption else None,
                progress_callback=progress_callback,
            )
            self._set_progress("")

            log.write(f"[bold green]✓ Upload erfolgreich:[/] {file_name}")
            if caption:
                log.write(f"  Caption: {caption}")
            log.write("")

            # Nachricht im Log anzeigen
            now = datetime.datetime.now()
            me_name = display_name(self._me) if self._me else "Ich"
            log.write(f"[bold cyan]▸ {me_name}[/] [dim]({now.strftime('%H:%M')})[/]")
            nr = self._next_display_nr
            self._next_display_nr += 1
            # Dummy-Message für die Anzeige
            log.write(f"  {caption}" if caption else "")
            log.write(f"  [bold green]  [{nr}][/bold green] 📎 {file_name} ({format_file_size(file_size)}) [dim]— gesendet[/]")
            log.write("")

            await self.load_dialogs()

        except Exception as e:
            self._set_progress("")
            log.write(f"[bold red]✗ Upload fehlgeschlagen:[/] {e}")
            log.write("")

    async def _handle_download(self, args):
        """Lädt ein Medium herunter."""
        log = self.query_one("#message-log", RichLog)

        if not self._media_map:
            log.write("[bold red]Keine Medien in diesem Chat gefunden.[/]")
            log.write("")
            return

        # Nummer bestimmen
        if args:
            try:
                nr = int(args[0])
            except ValueError:
                log.write(f"[bold red]Ungültige Nummer:[/] {args[0]}")
                log.write("")
                return
        else:
            # Letzte Nachricht mit Medien
            nr = max(self._media_map.keys())

        if nr not in self._media_map:
            log.write(f"[bold red]Kein Medium mit Nr. {nr}.[/]")
            log.write(f"[dim]Verfügbare Nummern: {', '.join(str(k) for k in sorted(self._media_map.keys()))}[/]")
            log.write("")
            return

        message = self._media_map[nr]
        desc = media_description(message)

        log.write(f"[bold]Download:[/] [{nr}] {desc}...")

        # Progress-Callback
        last_percent = [-1]

        def progress_callback(received, total):
            if total > 0:
                percent = int(received / total * 100)
                if percent >= last_percent[0] + 5 or percent >= 100:
                    last_percent[0] = percent
                    self._set_progress(f"Download: {percent}% ({format_file_size(received)}/{format_file_size(total)})")

        try:
            result = await self.client.download_media(
                message,
                file=str(DOWNLOAD_DIR),
                progress_callback=progress_callback,
            )
            self._set_progress("")

            if result:
                # result ist der gespeicherte Dateipfad
                saved_name = os.path.basename(str(result))
                saved_path = str(result)
                log.write(f"[bold green]✓ Gespeichert:[/] {saved_path}")
                log.write("")
            else:
                log.write("[bold yellow]Kein Medium zum Herunterladen.[/]")
                log.write("")

        except Exception as e:
            self._set_progress("")
            log.write(f"[bold red]✗ Download fehlgeschlagen:[/] {e}")
            log.write("")

    async def _list_media(self):
        """Listet alle Medien im aktuellen Chat auf."""
        log = self.query_one("#message-log", RichLog)

        if not self._media_map:
            log.write("[bold]Keine Medien in diesem Chat.[/]")
            log.write("")
            return

        log.write("[bold]=== Medien in diesem Chat ===[/]")
        for nr in sorted(self._media_map.keys()):
            msg = self._media_map[nr]
            desc = media_description(msg)
            sender = None
            if msg.sender_id:
                try:
                    sender = await self.client.get_entity(msg.sender_id)
                except Exception:
                    pass
            sender_name = display_name(sender) if sender else "?"
            time_str = format_timestamp(msg.date)
            log.write(f"  [bold green][{nr}][/bold green] {desc}")
            log.write(f"    [dim]von {sender_name}, {time_str} — /download {nr}[/]")
        log.write(f"[dim]Speicherort: {DOWNLOAD_DIR}[/]")
        log.write("")

    # --- Actions für Keybindings ---
    async def action_refresh(self) -> None:
        """Aktualisiert die Chatliste und Nachrichten."""
        await self.load_dialogs()
        if self.current_chat:
            await self.load_messages(self.current_chat)

    async def action_focus_chats(self) -> None:
        self.query_one("#chat-list", ListView).focus()

    async def action_focus_input(self) -> None:
        self.query_one("#message-input", Input).focus()

    async def action_upload(self) -> None:
        """Füllt /upload im Eingabefeld vor."""
        inp = self.query_one("#message-input", Input)
        inp.value = "/upload "
        inp.focus()
        inp.cursor_position = len(inp.value)

    async def action_download_last(self) -> None:
        """Lädt das letzte Medium im aktuellen Chat herunter."""
        if not self._media_map:
            log = self.query_one("#message-log", RichLog)
            log.write("[bold red]Keine Medien in diesem Chat.[/]")
            log.write("")
            return
        await self._handle_download([])

    async def on_unmount(self) -> None:
        """Wird beim Beenden aufgerufen."""
        if self.client:
            await self.client.disconnect()


# --- Einstiegspunkt ---
def main():
    check_api_credentials()

    # Login im Terminal durchführen (vor dem TUI-Start)
    # Verwende eine temporäre Loop für den Login
    login_client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    do_login(login_client)

    # TUI starten — Textual erstellt seine eigene Event-Loop,
    # auf der Telethon dann weiterläuft (Reconnect in on_mount)
    app = TelecliApp(int(API_ID), API_HASH)
    app.run()


if __name__ == "__main__":
    main()
