# Restaurant Tinel: rezervacije stolova

Projekt iz kolegija **Programiranje za web** na SIT UNIZD.

Gosti rezerviraju stolove u restoranu Tinel, a restoran (admin) upravlja
stolovima i vidi sve rezervacije.

## Domena

**Uloge**

- `admin`: restoran; upravlja stolovima, vidi sve rezervacije, otkazuje bilo
  koju rezervaciju i označava goste koji nisu došli
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
4. Gost smije otkazati rezervaciju najkasnije 2 sata prije dolaska (u samom
   trenutku roka više ne); restoran smije uvijek.
5. Restoran drži stol 30 minuta nakon dogovorenog vremena; od tog trenutka
   admin smije označiti da gost nije došao (`no_show`).

Statusi rezervacije: `active`, `cancelled`, `no_show`. Rezervacija se ne briše;
otkazivanje i nedolazak su prijelazi stanja s vlastitom adresom.

## Struktura

```
api/                 # backend: FastAPI
  app/
    main.py          # sastavljanje aplikacije
    seed.py          # početni podatci
    core/            # konfiguracija, baza, lozinke, JWT, ovisnosti, pogreške
    routers/         # rute: primaju zahtjev, vraćaju odgovor
    schemas/         # Pydantic sheme ulaza i izlaza
    services/        # poslovna pravila
    repositories/    # upiti nad bazom
    models/          # SQLAlchemy modeli (tablice)
  alembic/           # migracije
  tests/             # pytest
docker-compose.yml   # baza podataka
.env.example         # predložak konfiguracije
```

## Preduvjeti

- Git
- Python 3.11 ili noviji
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop s alatom Docker Compose

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

Provjera: http://127.0.0.1:8000/health vraća `{"status": "ok"}`, a
http://127.0.0.1:8000/docs prikazuje Swagger UI s popisom ruta.

### Početni podatci

`python -m app.seed` stvara admina, dva gosta, pet stolova i jednu primjer
rezervaciju. Smije se pokrenuti više puta; što već postoji, ne stvara se ponovno.

| Uloga | Prijava | Lozinka |
|-------|---------|---------|
| admin | `admin@tinel.hr` | `admin123` |
| guest | `ana@tinel.hr` | `ana12345` |
| guest | `marko@tinel.hr` | `marko123` |

## Krajnje točke

| Metoda | Putanja | Tko | Opis |
|--------|---------|-----|------|
| GET | `/health/` | svi | provjera rada |
| POST | `/auth/register` | svi | registracija gosta |
| POST | `/auth/login` | svi | prijava, vraća access i refresh token |
| POST | `/auth/refresh` | svi | novi par tokena |
| GET | `/auth/me` | prijavljeni | podatci o prijavljenom korisniku |
| GET | `/tables/` | prijavljeni | popis stolova (`location`, `limit`, `offset`) |
| GET | `/tables/{id}` | prijavljeni | jedan stol |
| POST | `/tables/` | admin | novi stol |
| PATCH | `/tables/{id}` | admin | izmjena stola |
| DELETE | `/tables/{id}` | admin | brisanje stola bez rezervacija |
| GET | `/reservations/` | admin, guest | popis (`status`, `limit`, `offset`); gost vidi samo svoje |
| GET | `/reservations/{id}` | admin, vlasnik | jedna rezervacija |
| POST | `/reservations/` | guest | nova rezervacija |
| POST | `/reservations/{id}/cancel` | admin, vlasnik | otkazivanje |
| POST | `/reservations/{id}/no-show` | admin | gost nije došao |

Popisi primaju `limit` (zadano 20, najviše 100) i `offset` (zadano 0).

## Pogreške

Svaki neuspjeh vraća tijelo istoga oblika:

```json
{ "code": "not_found", "message": "Stol nije pronađen" }
```

`code` je stalan i namijenjen kodu klijenta, `message` je namijenjen čovjeku.
Pogreška u obliku podataka, sa statusom 422, uz to nosi polje `errors` s
popisom polja koja nisu prošla provjeru.

409 nosi jedino sukob s postojećim zapisom, 422 jedino pogrešku u obliku
podataka, a ostala odbijena pravila vraćaju 400.

| code | Status | Kada |
|------|--------|------|
| `validation_error` | 422 | tijelo ili parametri ne odgovaraju shemi |
| `invalid_credentials` | 401 | prijava ili token ne vrijede |
| `token_expired` | 401 | pristupni token je istekao |
| `forbidden` | 403 | uloga ili vlasništvo ne dopušta radnju |
| `not_found` | 404 | zapis ili putanja ne postoji |
| `duplicate` | 409 | zauzeto korisničko ime ili broj stola |
| `table_has_reservations` | 409 | stol s rezervacijama ne može se obrisati |
| `table_taken` | 409 | stol je u tom terminu već rezerviran |
| `over_capacity` | 400 | broj osoba je veći od kapaciteta stola |
| `start_in_past` | 400 | vrijeme rezervacije je prošlo |
| `cancel_deadline_passed` | 400 | do dolaska je manje od 2 sata |
| `too_early` | 400 | od dolaska još nije prošlo 30 minuta |
| `not_active` | 400 | rezervacija je već otkazana ili označena kao nedolazak |

## Baza podataka i migracije

Shema baze mijenja se isključivo migracijama, koje stoje u
`api/alembic/versions/`.

```powershell
cd api
alembic revision --autogenerate --rev-id 002 -m "opis promjene"
alembic upgrade head      # primijeni sve što još nije primijenjeno
alembic downgrade -1      # poništi zadnju migraciju
alembic current           # na kojoj je migraciji baza
```

Svaka nastala migracija čita se prije pokretanja.

### Prazna baza

```powershell
docker compose down -v        # briše kontejner i volumen s podatcima
docker compose up -d db
cd api
alembic upgrade head
python -m app.seed
```

## Testovi

```powershell
docker compose up -d db
cd api
pytest
```

Testovi rade nad zasebnom bazom `rezervacije_test` na istom poslužitelju; stvara
se sama pri prvom pokretanju, a tablice se prazne prije svakog testa. Pravila
koja ovise o vremenu testiraju se sa zamrznutim vremenom (freezegun), svaka
granica zasebno.

## Kvaliteta koda

```powershell
cd api
ruff format .     # jedinstven stil
ruff check .      # pogreške vidljive iz koda
```

## Commitovi

Poruke prate oblik `vrsta(dio): namjera`, npr. `feat(api): add tables CRUD`.
Vrste: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
