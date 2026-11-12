# Rezervacije stolova u restoranu

Projekt iz kolegija **Programiranje za web** na SIT UNIZD.

Gosti rezerviraju stolove u restoranu, a restoran (admin) upravlja stolovima i
vidi sve rezervacije.

## Struktura

```
api/                 # backend: FastAPI
  app/
    main.py          # sastavljanje aplikacije
    core/            # konfiguracija, zapisnik
    routers/         # rute: primaju zahtjev, vraćaju odgovor
docker-compose.yml   # baza podataka
.env.example         # predložak konfiguracije
```

## Pokretanje (PowerShell)

```powershell
# 1) Konfiguracija
Copy-Item .env.example .env

# 2) Baza (Docker Desktop mora biti upaljen)
docker compose up -d db

# 3) Backend
cd api
uv venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
uvicorn app.main:app --reload
```

Provjera: http://127.0.0.1:8000/health vraća `{"status": "ok"}`, a
http://127.0.0.1:8000/docs prikazuje Swagger UI.
