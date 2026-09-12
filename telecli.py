#!/usr/bin/env python3
"""
Telecli — Terminal-basierter Telegram-Client
Telethon läuft in einem separaten Thread mit eigener Event-Loop.
"""

import asyncio
import os
import sys
import shlex
import threading
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

# --- Konfiguration ---
CONFIG_DIR = Path.home() / ".config" / "telecli"
SESSION_NAME = str(CONFIG_DIR / "session")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_DIR = Path(os.environ.get("TG_DOWNLOAD_DIR", str(Path.home() / "Downloads" / "telecli")))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

API_ID = os.environ.get("TG_API_ID")
API_HASH = os.environ.get("TG_API_HASH")


def check_api_credentials():
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
        sys.exit(1)


# --- Hilfsfunktionen ---
def display_name(entity):
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
    if isinstance(entity, User):
        return "👤"
    if isinstance(entity, Channel):
        return "📢"
    if isinstance(entity, Chat):
        return "👥"
    return "💬"


def format_timestamp(dt):
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
    icon = media_icon(message) or "📎"
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
    return message.media is not None and not (
        hasattr(message.media, "webpage") and message.media.webpage
    )


LOGIN_NONE = 0
LOGIN_PHONE = 1
LOGIN_CODE = 2
LOGIN_PASSWORD = 3


# --- Telegram Thread ---
class TelegramThread(threading.Thread):
    """Führt Telethon in einem separaten Thread mit eigener Event-Loop aus."""

    def __init__(self, api_id, api_hash, session_name):
        super().__init__(daemon=True)
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.loop = None
        self.client = None
        self.me = None
        # Status: "starting", "connecting", "login_needed", "ready", "error"
        self.status = "starting"
        self.error = None
        self._login_phone = None
        self._login_result = None
        self._login_event = threading.Event()
        self._stop = False

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main())
        except Exception as e:
            self.status = "error"
            self.error = str(e)

    async def _main(self):
        """Telethon Haupt-Loop."""
        self.status = "connecting"
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.connect()
        except Exception as e:
            self.status = "error"
            self.error = f"Verbindungsfehler: {e}"
            return

        try:
            authorized = await self.client.is_user_authorized()
        except Exception as e:
            self.status = "error"
            self.error = f"Login-Prüfung fehlgeschlagen: {e}"
            return

        if not authorized:
            self.status = "login_needed"
            # Auf Login-Daten vom Hauptthread warten
            while not self._stop:
                self._login_event.wait(timeout=1.0)
                if self._stop:
                    return
                if self._login_phone is not None:
                    self._login_result = None
                    self._login_event.clear()
                    await self._do_login()
                    if self._login_result == "ok":
                        break
                    # Bei Fehler: erneut auf Eingabe warten
                    self._login_phone = None
                    self.status = "login_needed"
        else:
            try:
                self.me = await self.client.get_me()
                self.status = "ready"
            except Exception as e:
                self.status = "error"
                self.error = f"Profil laden fehlgeschlagen: {e}"
                return

        # Event-Handler für eingehende Nachrichten
        @self.client.on(events.NewMessage(incoming=True))
        async def _on_new_message(event):
            pass  # Wird vom Hauptthread über Polling abgefragt

        # Loop am Leben halten
        while not self._stop:
            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break

    async def _do_login(self):
        """Führt den Login durch."""
        try:
            await self.client.send_code_request(self._login_phone)
            self.status = "login_code"
            self._login_result = "code_sent"

            # Auf Code warten
            while not self._stop:
                self._login_event.wait(timeout=1.0)
                if self._stop:
                    return
                if self._login_phone is not None:  # Code ist in _login_phone
                    code = self._login_phone
                    self._login_phone = None
                    self._login_event.clear()
                    try:
                        await self.client.sign_in(self._login_phone, code)
                        self._login_result = "ok"
                        self.me = await self.client.get_me()
                        self.status = "ready"
                        return
                    except SessionPasswordNeededError:
                        self.status = "login_password"
                        self._login_result = "need_password"
                    except Exception as e:
                        self._login_result = f"error: {e}"
                        self.status = "login_needed"
                        return
        except Exception as e:
            self._login_result = f"error: {e}"
            self.status = "login_needed"

    def submit_login(self, value):
        """Sendet einen Login-Wert an den Telethon-Thread."""
        self._login_phone = value
        self._login_event.set()

    def stop(self):
        """Stoppt den Telethon-Thread sauber."""
        self._stop = True
        self._login_event.set()
        # Telethon sauber trennen — auf Telethons eigener Event-Loop
        if self.loop and self.client:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.client.disconnect(), self.loop
                )
                future.result(timeout=5)
            except Exception:
                pass
        # Alle verbleibenden Tasks abbrechen
        if self.loop:
            try:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass

    def call(self, coro, timeout=30):
        """Ruft eine Coroutine auf Telethons Event-Loop auf und gibt das Ergebnis zurück."""
        if not self.loop or not self.client:
            raise RuntimeError("Telegram nicht verbunden")
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)


# --- TUI Application ---
class TelecliApp(App):
    """Hauptanwendung für Telecli."""

    CSS = """
    Screen { background: $surface; }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #chat-panel {
        width: 35;
        border: solid $primary;
        background: $surface;
    }

    #message-panel {
        width: 1fr;
        border: solid $primary;
        background: $panel;
    }

    #chat-list {
        height: 1fr;
        scrollbar-size: 0 0;
    }

    #chat-list > ListItem {
        padding: 0 1;
        height: auto;
    }

    #chat-list > ListItem:hover {
        background: $boost;
    }

    #message-log {
        height: 1fr;
        border: none;
        padding: 0 1;
        scrollbar-size: 0 0;
    }

    #bottom-bar {
        dock: bottom;
        height: 6;
    }

    #input-panel {
        height: 4;
        border: solid $primary;
        background: $surface;
        padding: 0 1;
    }

    #message-input {
        height: 1fr;
        color: $text;
        background: $surface;
        border: none;
    }

    #status-bar {
        height: 1;
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

    def __init__(self, api_id: int, api_hash: str):
        super().__init__()
        self.api_id = api_id
        self.api_hash = api_hash
        self._tg = None
        self._me = None
        self._messages = []
        self._media_map = {}
        self._next_display_nr = 1
        self._progress_text = ""
        self._login_state = LOGIN_NONE
        self._login_phone = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-container"):
            with Vertical(id="chat-panel"):
                yield ListView(id="chat-list")
            with Vertical(id="message-panel"):
                yield RichLog(id="message-log", markup=True)
        with Vertical(id="bottom-bar"):
            with Vertical(id="input-panel"):
                yield Input(id="message-input", placeholder="Nachricht schreiben... (/help für Hilfe)")
            yield Label(id="status-bar", markup=True)

    def on_mount(self) -> None:
        log = self.query_one("#message-log", RichLog)
        log.write("[bold]Telecli wird gestartet...[/]")
        log.write("")
        self.query_one("#status-bar", Label).update(" Verbinde mit Telegram...")

        # Telethon in separatem Thread starten
        self._tg = TelegramThread(self.api_id, self.api_hash, SESSION_NAME)
        self._tg.start()

        # Status pollen
        self.set_timer(0.5, self._poll_status)

    def _poll_status(self):
        """Pollt den Verbindungsstatus."""
        if not self._tg:
            return

        status = self._tg.status
        log = self.query_one("#message-log", RichLog)
        sb = self.query_one("#status-bar", Label)

        if status == "connecting":
            sb.update(" Verbinde...")
            self.set_timer(0.5, self._poll_status)

        elif status == "login_needed":
            self._login_state = LOGIN_PHONE
            log.write("[bold]═══ Telegram-Login ═══[/]")
            log.write("")
            log.write("Telefonnummer mit Ländervorwahl eingeben.")
            log.write("Beispiel: +491701234567")
            log.write("")
            inp = self.query_one("#message-input", Input)
            inp.placeholder = "Telefonnummer (z.B. +49...)"
            sb.update(" Login erforderlich")
            inp.focus()

        elif status == "login_code":
            self._login_state = LOGIN_CODE
            log.write("[bold green]Code gesendet![/] Bestätigungscode eingeben:")
            inp = self.query_one("#message-input", Input)
            inp.placeholder = "Bestätigungscode"
            sb.update(" Code eingeben")
            inp.focus()

        elif status == "login_password":
            self._login_state = LOGIN_PASSWORD
            log.write("Zwei-Faktor-Authentifizierung. Passwort eingeben:")
            inp = self.query_one("#message-input", Input)
            inp.placeholder = "Passwort"
            sb.update(" 2FA-Passwort")
            inp.focus()

        elif status == "ready":
            self._login_state = LOGIN_NONE
            self._me = self._tg.me
            inp = self.query_one("#message-input", Input)
            inp.placeholder = "Nachricht schreiben... (/help für Hilfe)"
            sb.update(" Lade Chats...")
            log.clear()
            log.write("[bold green]Verbunden![/] Lade Chats...")
            self.set_timer(0.1, self._load_dialogs)

        elif status == "error":
            log.write(f"[bold red]Fehler:[/] {self._tg.error}")
            sb.update(" Fehler")
            log.write("")
            log.write("Versuche: rm ~/.config/telecli/session.session")

        else:
            self.set_timer(0.5, self._poll_status)

    def _load_dialogs(self):
        """Lädt die Chatliste in einem Hintergrund-Thread."""
        def _load():
            try:
                dialogs = self._tg.call(self._tg.client.get_dialogs(limit=100))
                self._render_dialogs(dialogs)
            except Exception as e:
                log = self.query_one("#message-log", RichLog)
                log.write(f"[bold red]Fehler beim Laden der Chats:[/] {e}")

        threading.Thread(target=_load, daemon=True).start()

    def _render_dialogs(self, dialogs):
        """Rendert die Chatliste (wird aus Hintergrund-Thread aufgerufen)."""
        # UI-Updates müssen auf Textuals Event-Loop
        self.call_from_thread(self._do_render_dialogs, dialogs)

    async def _do_render_dialogs(self, dialogs):
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
                preview = "..."
            else:
                preview = ""
            time_str = format_timestamp(dialog.date)
            label_text = f"{icon} {name}\n   {truncate(preview, 28)}  {time_str}"
            item = ListItem(Label(label_text))
            item.dialog = dialog
            chat_list.append(item)
        self._update_status_bar()

    def _update_status_bar(self):
        status = self.query_one("#status-bar", Label)
        if self._login_state:
            return
        if not self._me:
            status.update(" Verbinde...")
            return
        me_name = display_name(self._me)
        chat_name = display_name(self.current_chat.entity) if self.current_chat else "Kein Chat"
        progress = f" | {self._progress_text}" if self._progress_text else ""
        status.update(f" {me_name} | Chat: {chat_name}{progress}")

    def _set_progress(self, text):
        self._progress_text = text
        self._update_status_bar()

    @on(ListView.Selected, "#chat-list")
    async def on_chat_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if hasattr(item, "dialog"):
            self.current_chat = item.dialog
            self._update_status_bar()
            await self._load_messages(item.dialog)

    async def _load_messages(self, dialog):
        log = self.query_one("#message-log", RichLog)
        log.clear()
        log.write(f"[bold]=== {display_name(dialog.entity)} ===[/]\n")

        self._messages = []
        self._media_map = {}
        self._next_display_nr = 1

        def _fetch():
            try:
                messages = self._tg.call(
                    self._tg.client.get_messages(dialog.entity, limit=100)
                )
                self.call_from_thread(self._render_messages, list(reversed(messages)))
            except Exception as e:
                self.call_from_thread(self._show_error, str(e))

        threading.Thread(target=_fetch, daemon=True).start()

    async def _render_messages(self, messages):
        log = self.query_one("#message-log", RichLog)
        for msg in messages:
            await self._append_message(msg)
        log.write("")

    async def _show_error(self, error):
        log = self.query_one("#message-log", RichLog)
        log.write(f"[bold red]Fehler:[/] {error}")

    async def _append_message(self, message):
        log = self.query_one("#message-log", RichLog)

        sender = None
        if message.sender_id:
            try:
                sender = self._tg.call(
                    self._tg.client.get_entity(message.sender_id), timeout=10
                )
            except Exception:
                pass
        sender_name = display_name(sender) if sender else "Unbekannt"
        time_str = format_timestamp(message.date)
        is_me = message.sender_id == self._me.id if self._me else False
        self._messages.append(message)

        if is_me:
            prefix = f"[bold cyan]▸ {sender_name}[/]"
        else:
            prefix = f"[bold yellow]◂ {sender_name}[/]"

        log.write(f"{prefix} [dim]({time_str})[/]")
        if message.text:
            log.write(f"  {message.text}")

        if has_media(message):
            nr = self._next_display_nr
            self._next_display_nr += 1
            self._media_map[nr] = message
            desc = media_description(message)
            log.write(f"  [bold green]  [{nr}][/bold green] {desc} [dim]— /download {nr}[/]")
        log.write("")

    @on(Input.Submitted, "#message-input")
    async def on_message_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            return
        event.input.value = ""

        if self._login_state != LOGIN_NONE:
            await self._handle_login_input(raw)
            return

        if raw.startswith("/"):
            await self._handle_command(raw)
        else:
            if not self.current_chat:
                return
            await self._send_text(raw)

    async def _handle_login_input(self, value: str):
        log = self.query_one("#message-log", RichLog)
        inp = self.query_one("#message-input", Input)

        if self._login_state == LOGIN_PHONE:
            self._login_phone = value
            log.write(f"Telefonnummer: {value}")
            log.write("Sende Bestätigungscode...")
            self._tg.submit_login(value)
            self.set_timer(0.5, self._poll_status)

        elif self._login_state == LOGIN_CODE:
            log.write(f"Code: {'*' * len(value)}")
            self._tg.submit_login(value)
            self.set_timer(0.5, self._poll_status)

        elif self._login_state == LOGIN_PASSWORD:
            log.write("Passwort: ******")
            self._tg.submit_login(value)
            self.set_timer(0.5, self._poll_status)

    async def _send_text(self, text: str):
        def _send():
            try:
                self._tg.call(
                    self._tg.client.send_message(self.current_chat.entity, text)
                )
                self.call_from_thread(self._after_send, text)
            except Exception as e:
                self.call_from_thread(self._show_error, str(e))

        threading.Thread(target=_send, daemon=True).start()

    def _after_send(self, text):
        log = self.query_one("#message-log", RichLog)
        now = datetime.datetime.now()
        me_name = display_name(self._me) if self._me else "Ich"
        log.write(f"[bold cyan]▸ {me_name}[/] [dim]({now.strftime('%H:%M')})[/]")
        log.write(f"  {text}")
        log.write("")
        self._load_dialogs()

    async def _handle_command(self, raw: str):
        log = self.query_one("#message-log", RichLog)

        try:
            parts = shlex.split(raw)
        except ValueError as e:
            log.write(f"[bold red]Fehler:[/] {e}")
            return

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "/help":
            log.write("[bold]=== Befehle ===[/]")
            log.write("  [green]/upload[/] <pfad> [caption]  Datei/Bild senden")
            log.write("  [green]/download[/] [nr]           Medium herunterladen")
            log.write("  [green]/media[/]                   Medien auflisten")
            log.write("  [green]/refresh[/]                 Aktualisieren")
            log.write("  [green]/help[/]                    Hilfe")
            log.write("  [green]/quit[/]                    Beenden")
            log.write("")

        elif cmd == "/quit":
            self.exit()

        elif cmd == "/refresh":
            await self.load_dialogs()
            if self.current_chat:
                await self._load_messages(self.current_chat)

        elif cmd == "/upload":
            if not self.current_chat:
                log.write("[bold red]Kein Chat![/]")
                return
            await self._handle_upload(args)

        elif cmd == "/download":
            if not self.current_chat:
                log.write("[bold red]Kein Chat![/]")
                return
            await self._handle_download(args)

        elif cmd == "/media":
            await self._list_media()

        else:
            log.write(f"[bold red]Unbekannt:[/] {cmd} — /help")

    async def _handle_upload(self, args):
        log = self.query_one("#message-log", RichLog)

        if not args:
            log.write("[bold red]Verwendung:[/] /upload <pfad> [caption]")
            return

        file_path = os.path.expanduser(args[0])
        caption = " ".join(args[1:]) if len(args) > 1 else ""

        if not os.path.exists(file_path):
            log.write(f"[bold red]Datei nicht gefunden:[/] {file_path}")
            return

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        log.write(f"[bold]Upload:[/] {file_name} ({format_file_size(file_size)})...")

        def _upload():
            try:
                last_pct = [-1]
                def cb(sent, total):
                    if total > 0:
                        pct = int(sent / total * 100)
                        if pct >= last_pct[0] + 5 or pct >= 100:
                            last_pct[0] = pct
                            self.call_from_thread(lambda: self._set_progress(f"Upload: {pct}%"))

                self._tg.call(
                    self._tg.client.send_file(
                        self.current_chat.entity, file_path,
                        caption=caption if caption else None,
                        progress_callback=cb,
                    )
                )
                self.call_from_thread(lambda: self._set_progress(""))
                self.call_from_thread(lambda: log.write(f"[bold green]✓ Upload OK:[/] {file_name}"))
                self.call_from_thread(lambda: log.write(""))
                self.call_from_thread(self._load_dialogs)
            except Exception as e:
                self.call_from_thread(lambda: self._set_progress(""))
                self.call_from_thread(lambda: log.write(f"[bold red]✗ Upload fehlgeschlagen:[/] {e}"))

        threading.Thread(target=_upload, daemon=True).start()

    async def _handle_download(self, args):
        log = self.query_one("#message-log", RichLog)

        if not self._media_map:
            log.write("[bold red]Keine Medien.[/]")
            return

        if args:
            try:
                nr = int(args[0])
            except ValueError:
                log.write(f"[bold red]Ungültige Nummer.[/]")
                return
        else:
            nr = max(self._media_map.keys())

        if nr not in self._media_map:
            log.write(f"[bold red]Kein Medium Nr. {nr}.[/]")
            return

        message = self._media_map[nr]
        desc = media_description(message)
        log.write(f"[bold]Download:[/] [{nr}] {desc}...")

        def _download():
            try:
                last_pct = [-1]
                def cb(recvd, total):
                    if total > 0:
                        pct = int(recvd / total * 100)
                        if pct >= last_pct[0] + 5 or pct >= 100:
                            last_pct[0] = pct
                            self.call_from_thread(lambda: self._set_progress(f"Download: {pct}%"))

                result = self._tg.call(
                    self._tg.client.download_media(
                        message, file=str(DOWNLOAD_DIR), progress_callback=cb
                    )
                )
                self.call_from_thread(lambda: self._set_progress(""))
                if result:
                    self.call_from_thread(lambda: log.write(f"[bold green]✓ Gespeichert:[/] {result}"))
                else:
                    self.call_from_thread(lambda: log.write("[bold yellow]Kein Medium.[/]"))
                self.call_from_thread(lambda: log.write(""))
            except Exception as e:
                self.call_from_thread(lambda: self._set_progress(""))
                self.call_from_thread(lambda: log.write(f"[bold red]✗ Download fehlgeschlagen:[/] {e}"))

        threading.Thread(target=_download, daemon=True).start()

    async def _list_media(self):
        log = self.query_one("#message-log", RichLog)
        if not self._media_map:
            log.write("[bold]Keine Medien.[/]")
            return
        log.write("[bold]=== Medien ===[/]")
        for nr in sorted(self._media_map.keys()):
            msg = self._media_map[nr]
            desc = media_description(msg)
            time_str = format_timestamp(msg.date)
            log.write(f"  [bold green][{nr}][/bold green] {desc}")
            log.write(f"    [dim]{time_str} — /download {nr}[/]")
        log.write(f"[dim]Speicherort: {DOWNLOAD_DIR}[/]")
        log.write("")

    # --- Actions ---
    async def action_refresh(self):
        await self.load_dialogs()
        if self.current_chat:
            await self._load_messages(self.current_chat)

    async def load_dialogs(self):
        self._load_dialogs()

    async def action_focus_chats(self):
        self.query_one("#chat-list", ListView).focus()

    async def action_focus_input(self):
        self.query_one("#message-input", Input).focus()

    async def action_upload(self):
        inp = self.query_one("#message-input", Input)
        inp.value = "/upload "
        inp.focus()
        inp.cursor_position = len(inp.value)

    async def action_download_last(self):
        if not self._media_map:
            log = self.query_one("#message-log", RichLog)
            log.write("[bold red]Keine Medien.[/]")
            return
        await self._handle_download([])

    def on_unmount(self) -> None:
        if self._tg:
            self._tg.stop()


# --- Einstiegspunkt ---
def main():
    check_api_credentials()
    app = TelecliApp(int(API_ID), API_HASH)
    app.run()


if __name__ == "__main__":
    main()
