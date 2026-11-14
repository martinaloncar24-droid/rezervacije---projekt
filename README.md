# Restaurant Tinel: rezervacije stolova

Projekt iz kolegija **Programiranje za web** na SIT UNIZD.

Gosti rezerviraju stolove u restoranu Tinel, a restoran (admin) upravlja
stolovima i vidi sve rezervacije.

## Domena

**Uloge**

- `admin`: restoran; upravlja stolovima, vidi sve rezervacije, označava
  goste koji nisu došli
- `guest`: gost; vidi, stvara i otkazuje samo svoje rezervacije

**Tablice**

- `users`: korisnički računi (korisničko ime, hash lozinke, uloga)
- `dining_tables`: stolovi (broj stola, kapacitet, lokacija `terasa` ili `ulica`)
- `reservations`: rezervacije (gost, stol, vrijeme dolaska, broj osoba, status)

Jedan gost ima više rezervacija, jedan stol ima više rezervacija (veze 1:N).

**Poslovna pravila**

1. Broj osoba ne smije premašiti kapacitet stola.
2. Rezervacija traje 2 sata; isti stol ne smije imati dvije aktivne
   rezervacije koje se preklapaju.
3. Rezervacija mora biti u budućnosti.
4. Gost smije otkazati rezervaciju najkasnije 2 sata prije dolaska.
5. Restoran drži stol 30 minuta nakon dogovorenog vremena; tek tada admin
   smije označiti da gost nije došao (`no_show`).

Statusi rezervacije: `active`, `cancelled`, `no_show`.

## Struktura

```
api/                 # backend: FastAPI
  app/
    main.py          # sastavljanje aplikacije
    seed.py          # početni podatci
    core/            # konfiguracija, baza, lozinke, zapisnik
    routers/         # rute: primaju zahtjev, vraćaju odgovor
    models/          # SQLAlchemy modeli (tablice)
  alembic/           # migracije
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
alembic upgrade head          # stvara tablice
python -m app.seed            # početni podatci
uvicorn app.main:app --reload
```

### Početni podatci

`python -m app.seed` stvara admina, dva gosta, pet stolova i jednu primjer
rezervaciju. Smije se pokrenuti više puta; što već postoji, ne stvara se ponovno.

| Uloga | Prijava | Lozinka |
|-------|---------|---------|
| admin | `admin@tinel.hr` | `admin123` |
| guest | `ana@tinel.hr` | `ana12345` |
| guest | `marko@tinel.hr` | `marko123` |

### Migracije

```powershell
cd api
alembic revision --autogenerate --rev-id 002 -m "opis promjene"
alembic upgrade head      # primijeni sve što još nije primijenjeno
alembic downgrade -1      # poništi zadnju migraciju
alembic current           # na kojoj je migraciji baza
```

Svaka nastala migracija čita se prije pokretanja.

Provjera: http://127.0.0.1:8000/health vraća `{"status": "ok"}`, a
http://127.0.0.1:8000/docs prikazuje Swagger UI.
