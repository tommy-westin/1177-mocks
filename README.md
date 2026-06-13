# 1177 VVH Mock Server

Mock-server för 1177 NTjP-tjänstekontrakt. Implementerar SOAP-endpoints för `carelisting` och `person`, samt REST-endpoints för filhantering och administration.

Se [API.md](API.md) för fullständig endpoint-dokumentation.

---

## Innehåll

- [Alternativ 1 – Docker (Proxmox / Linux)](#alternativ-1--docker-proxmox--linux)
- [Alternativ 2 – Lokalt på Windows](#alternativ-2--lokalt-på-windows)
- [Uppdatera servern](#uppdatera-servern)
- [Testa att det fungerar](#testa-att-det-fungerar)

---

## Alternativ 1 – Docker (Proxmox / Linux)

Kör servern i en Docker-container med Cloudflare Tunnel för extern åtkomst. Lämpligt för ett delat testmiljö som kollegor kan nå från jobbet.

### Förutsättningar

- Proxmox LXC-container med Debian 12
- Docker installerat
- Cloudflare-konto med en domän

### 1. Skapa LXC-container i Proxmox

```bash
pveam download local debian-12-standard_12.7-1_amd64.tar.zst

pct create 200 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname 1177-mock \
  --memory 512 \
  --cores 1 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1

pct start 200
pct enter 200
```

### 2. Installera Docker

```bash
apt update && apt install -y curl git
curl -fsSL https://get.docker.com | sh
```

### 3. Klona repot

```bash
git clone https://github.com/tommy-westin/1177-mocks /opt/1177-mocks
cd /opt/1177-mocks
```

### 4. Skapa Cloudflare Tunnel

1. Gå till **Cloudflare Zero Trust → Networks → Tunnels → Create a tunnel**
2. Namn: `1177-mock`, välj Docker-alternativet och kopiera token
3. Under **Public Hostname**: lägg till din domän, service: `http://vvh-mocks:8088`

### 5. Konfigurera miljövariabler

```bash
cp .env.example .env
nano .env
```

```env
MOCK_HOST=https://1177-mock.din-domän.com
CF_TUNNEL_TOKEN=eyJ...  # token från Cloudflare
ADMIN_API_KEY=välj-en-lång-slumpmässig-sträng  # skyddar /admin/* och /scenario/*
```

### 6. Starta

```bash
docker compose up -d
```

Första uppstarten skapar `config/data.db` automatiskt från JSON-filerna.

### Skydda /scenario och /admin med Cloudflare Access

1. **Zero Trust → Access → Applications → Add → Self-hosted**
2. Skapa en applikation för path `scenario` och en för `admin`
3. Policy: Allow → Emails → din e-postadress

### API-nyckel för admin-endpoints

Sätt `ADMIN_API_KEY` i `.env` (se ovan). Skicka nyckeln som header `X-Api-Key` i varje anrop mot `/admin/*` och `POST /scenario/*`.

**Exempel – hämta och ändra data:**

```bash
# Hämta alla patienter
curl -H "X-Api-Key: din-nyckel" https://1177-mock.din-domän.com/admin/patients

# Uppdatera en patient
curl -X PUT \
  -H "X-Api-Key: din-nyckel" \
  -H "Content-Type: application/json" \
  -d '{"facilityHsaId": "SE2321000156-E000001", "isInQueue": false}' \
  https://1177-mock.din-domän.com/admin/patients/190101019999

# Byta aktivt scenario
curl -X POST \
  -H "X-Api-Key: din-nyckel" \
  https://1177-mock.din-domän.com/scenario/massavflyttning

# Återskapa databas från JSON
curl -X POST \
  -H "X-Api-Key: din-nyckel" \
  https://1177-mock.din-domän.com/admin/rebuild-db
```

**I webbläsaren** – scenario-sidan (`/scenario`) har ett nyckel-fält längst upp. Ange nyckeln där; den sparas i sessionStorage för resten av sessionen.

> **Lokal dev (Windows):** Lämna `ADMIN_API_KEY` tom i `.env` – då krävs ingen nyckel.

---

## Alternativ 2 – Lokalt på Windows

Kör servern direkt på din dator. Lämpligt för lokal testning utan Docker eller nätverksåtkomst.

### Förutsättningar

- Windows 10/11
- [Python 3.11+](https://www.python.org/downloads/) – kryssa i **"Add to PATH"** under installationen
- [Git](https://git-scm.com/download/win)

### 1. Klona repot

```powershell
git clone https://github.com/tommy-westin/1177-mocks C:\1177-mocks
cd C:\1177-mocks
```

### 2. Installera beroenden

```powershell
pip install -r requirements.txt
```

> Om `lxml` misslyckas, testa: `pip install lxml --only-binary=:all:`

### 3. Starta

```powershell
python server.py
```

Servern startar på `http://localhost:8088`. Första körningen skapar `config\data.db` automatiskt.

Öppna `http://localhost:8088` i webbläsaren för att se alla tillgängliga endpoints.

### I SoapUI

Peka WSDL-URL:en mot `http://localhost:8088` istället för den externa domänen:

```
http://localhost:8088/carelisting/GetListing?wsdl
http://localhost:8088/person/GetPersonsForProfile?wsdl
```

---

## Uppdatera servern

### Docker (Proxmox)

```bash
pct enter 200   # eller SSH till containern
cd /opt/1177-mocks
git pull
docker compose up -d --build
```

> Om bara `config/`-filer ändrats (data, scenarier) räcker `git pull` — ingen rebuild behövs.

### Windows

```powershell
cd C:\1177-mocks
git pull
python server.py
```

---

## Testa att det fungerar

Kör testskriptet mot valfri miljö:

```bash
# Mot extern server
python test_remote.py

# Mot lokal Windows-server
# Ändra BASE-variabeln i test_remote.py till http://localhost:8088
python test_remote.py
```

Flaggor:

| Flagga | Beskrivning |
|--------|-------------|
| `--verbose` | Skriv ut full XML-respons |
| `--dump` | Spara svar till `test_responses/*.xml` |

---

## Databashantering

All mockdata lagras i `config/data.db` (SQLite). Redigera med t.ex. [DB Browser for SQLite](https://sqlitebrowser.org/).

### Återskapa från JSON

Om du vill återställa databasen till ursprungsdata:

```bash
# Lokalt
python create_db.py

# Via API
curl -X POST http://localhost:8088/admin/rebuild-db
```

### Byta scenario

```bash
# Via webbläsaren
http://localhost:8088/scenario

# Via API
curl -X POST http://localhost:8088/scenario/massavflyttning
curl -X POST http://localhost:8088/scenario/default
```
