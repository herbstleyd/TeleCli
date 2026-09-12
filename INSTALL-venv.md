# Telecli — Anleitung: Installation mit Python venv

Diese Anleitung zeigt, wie du Telecli in einer virtuellen Python-Umgebung (venv) einrichtest und startest. So bleiben die Abhängigkeiten sauber vom restlichen System getrennt.

## 1. Archiv entpacken

```bash
tar xzf telecli.tar.gz -C ~/telecli
cd ~/telecli
```

## 2. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
```

Das erstellt einen Ordner `.venv/` mit einer isolierten Python-Installation.

## 3. Virtuelle Umgebung aktivieren

```bash
source .venv/bin/activate
```

Du erkennst die Aktivierung am Prompt — er beginnt dann mit `(.venv)`.

## 4. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

## 5. API-Daten einrichten

Du benötigst `api_id` und `api_hash` von https://my.telegram.org:

1. Gehe zu https://my.telegram.org
2. Melde dich mit deiner Telefonnummer an
3. Klicke auf **API development tools**
4. Erstelle eine neue App (Name beliebig)
5. Kopiere `api_id` und `api_hash`

### Option A: Umgebungsvariablen (empfohlen)

```bash
export TG_API_ID='deine_api_id'
export TG_API_HASH='dein_api_hash'
```

Dauerhaft in `~/.bashrc`:

```bash
echo 'export TG_API_ID="deine_api_id"' >> ~/.bashrc
echo 'export TG_API_HASH="dein_api_hash"' >> ~/.bashrc
source ~/.bashrc
```

### Option B: .env-Datei

```bash
mkdir -p ~/.config/telecli
cp .env.example ~/.config/telecli/.env
nano ~/.config/telecli/.env
```

Trage dort deine API-Daten ein. Verwende dann `start.sh` zum Starten (lädt die .env automatisch).

## 6. Erster Start (Login)

```bash
python3 telecli.py
```

Beim ersten Mal wirst du im Terminal nach Folgendem gefragt:

1. **Telefonnummer** — mit Ländervorwahl, z.B. `+491701234567`
2. **Bestätigungscode** — kommt per Telegram auf ein anderes Gerät
3. **Zwei-Faktor-Passwort** — nur falls du 2FA aktiviert hast

Danach wird die Session gespeichert unter `~/.config/telecli/session.session`. Bei weiteren Starts entfällt der Login.

## 7. Telecli starten (ab dem zweiten Mal)

Jedes Mal, wenn du Telecli nutzen möchtest:

```bash
cd ~/telecli
source .venv/bin/activate
python3 telecli.py
```

Oder mit dem Startskript (aktiviert venv automatisch + lädt .env):

```bash
cd ~/telecli
./start.sh
```

Dafür muss `start.sh` angepasst sein (siehe unten).

## 8. venv wieder verlassen

Wenn du fertig bist:

```bash
deactivate
```

Der Prompt ändert sich zurück — die virtuelle Umgebung ist deaktiviert.

---

## start.sh anpassen (optional)

Damit `start.sh` die venv automatisch aktiviert, ersetze den Inhalt mit:

```bash
#!/bin/bash
# Startskript für Telecli mit venv
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HOME/.config/telecli/.env"

# .env laden falls vorhanden
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# venv aktivieren und App starten
source "$SCRIPT_DIR/.venv/bin/activate"
python3 "$SCRIPT_DIR/telecli.py"
```

Speichern und ausführbar machen:

```bash
chmod +x start.sh
```

Dann reicht ein einfaches:

```bash
./start.sh
```

---

## Shortcut: Alias anlegen

Damit du nicht jedes Mal `cd` und `source` tippen musst:

```bash
echo 'alias telecli="cd ~/telecli && source .venv/bin/activate && python3 telecli.py"' >> ~/.bashrc
source ~/.bashrc
```

Danach startest du Telecli einfach mit:

```bash
telecli
```

---

## Übersicht: Wichtige Pfade

| Pfad | Beschreibung |
|---|---|
| `~/telecli/.venv/` | Virtuelle Python-Umgebung |
| `~/.config/telecli/` | Konfigurationsordner |
| `~/.config/telecli/session.session` | Gespeicherte Telegram-Session |
| `~/.config/telecli/.env` | API-Daten (optional) |
| `~/Downloads/telecli/` | Heruntergeladene Medien |

## Aktualisierung

Wenn es eine neue Version von Telecli gibt:

```bash
cd ~/telecli
source .venv/bin/activate
pip install -r requirements.txt --upgrade
```

Ersetze dann `telecli.py` durch die neue Version.

## Deinstallation

```bash
# Virtuelle Umgebung entfernen
rm -rf ~/telecli/.venv

# Komplette App entfernen
rm -rf ~/telecli

# Konfiguration und Session entfernen
rm -rf ~/.config/telecli

# Heruntergeladene Medien entfernen
rm -rf ~/Downloads/telecli

# Alias entfernen (falls gesetzt)
# Entferne die Zeile mit 'alias telecli=' aus ~/.bashrc
```
