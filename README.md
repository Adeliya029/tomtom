# TomTom Traffic Index Ingestion (airsense)

Pipeline ingestion data kemacetan lalu lintas Jakarta dari API publik TomTom
Traffic Index. Skema output disamakan dengan dataset referensi Kaggle
`ForExportNewApi.csv` (BwandoWando).

## Sumber data

- Endpoint: `GET https://www.tomtom.com/traffic-index/api/live-traffic.json?city=IDN_jakarta_new`
- Endpoint ini adalah API yang dipakai halaman https://www.tomtom.com/traffic-index/.
- Tidak butuh API key. `TOMTOM_API_KEY` hanya disiapkan untuk kemungkinan migrasi
  ke API resmi.
- Satu respons berisi 169 snapshot per jam (sekitar 7 hari terakhir).

Region yang tersedia di registry: `IDN_jakarta_new` (default), `IDN_bandung_new`,
`IDN_medan_new`, `IDN_palembang_new`, `IDN_surabaya_new`.

## Cara menjalankan

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# salin konfigurasi
Copy-Item .env.example .env

# jalankan untuk Jakarta
.\.venv\Scripts\python.exe -m scraper

# beberapa kota sekaligus
.\.venv\Scripts\python.exe -m scraper --regions IDN_jakarta_new,IDN_bandung_new

# fetch tanpa menyimpan file
.\.venv\Scripts\python.exe -m scraper --no-save

# test dan lint
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check scraper tests
```

## CI (GitHub Actions)

Workflow: `.github/workflows/ci.yml`

- Trigger: `push` ke `main`/`dev`, `pull_request` ke `main`/`dev`, dan
  `workflow_dispatch` (manual).
- Job `Lint`: `ruff check scraper tests`.
- Job `Unit tests`: `pytest -q`.
- Job `Scrape smoke test` (hanya push/manual, tidak pada PR): menjalankan
  `python -m scraper`, menampilkan CSV, lalu mengunggah artifact
  `scrape-output-<run_id>`.

### Skenario branch sampai merge (contoh)

```powershell
# 1. pastikan kode ada di dev
git checkout dev
git add scraper tests .github .gitignore .env.example pyproject.toml requirements.txt requirements-dev.txt README.md
git commit -m "feat: add TomTom scraper and CI workflow"
git push origin dev

# 2. buat branch fitur dari dev
git checkout -b feature/ci-pipeline
git push -u origin feature/ci-pipeline

# 3. buka Pull Request feature/ci-pipeline -> dev di GitHub,
#    tunggu job Lint + Unit tests hijau, lalu Merge pull request.

# 4. setelah dev terbaru, buka Pull Request dev -> main,
#    tunggu CI hijau, lalu Merge pull request.
```

Setelah push ke `main`/`dev`, cek tab **Actions** untuk melihat job
`Scrape smoke test` dan artifact hasil scraping.

## Output

```text
data/
├─ raw/traffic_index/<region_id>/<YYYY-MM-DD>/<run_id>.json   # payload mentah + metadata
└─ processed/traffic_index/<YYYY-MM-DD>/<run_id>.csv           # data bersih
   processed/traffic_index/latest.csv                          # snapshot run terakhir
```

Kolom `processed/*.csv`:

| Kolom | Asal data |
| :--- | :--- |
| `Country` | metadata kota (`Indonesia`) |
| `City` | metadata kota (`Jakarta`) |
| `UpdateTimeUTC` | `updateTime` (epoch ms) dikonversi ke UTC |
| `JamsDelay` | `jamsDelay` |
| `TrafficIndexLive` | `trafficIndexLive` |
| `JamsLengthInKms` | `jamsLength` |
| `JamsCount` | `jamsCount` |
| `TrafficIndexWeekAgo` | `trafficIndexHistoric` |
| `UpdateTimeUTCWeekAgo` | `UpdateTimeUTC - 7 hari` |
| `TravelTimeLivePer10KmsMins` | `relTravelTimeLive * 10 / 60` |
| `TravelTimeHistoricPer10KmsMins` | `relTravelTimeHistoric * 10 / 60` |
| `MinsDelay` | selisih dua kolom travel time di atas |

## Struktur kode

```text
scraper/
├─ __main__.py    # CLI: python -m scraper
├─ config.py      # environment / .env
├─ cities.py      # registry region id -> nama kota & negara
├─ client.py      # HTTP + retry + validasi payload
├─ transform.py   # flatten JSON -> skema dataset
└─ storage.py     # simpan raw JSON & processed CSV
tests/
.github/workflows/ci.yml   # lint + unit test + scrape smoke test
pyproject.toml             # konfigurasi pytest
```

## Roadmap tugas CI/CD

1. [x] Kode scraping Python + output CSV/JSON
2. [x] Workflow CI (`lint` + `pytest`) dan skenario merge `dev -> main`
3. [ ] Workflow CD: upload hasil ke Azure Blob Storage (OIDC federated credential)
4. [ ] Scheduler `cron: 0 */6 * * *` + `workflow_dispatch`
5. [ ] Setup Azure Storage Account, App Registration, role assignment
6. [ ] Bukti: log GitHub Actions + file di Azure Blob

> Catatan: gunakan data secara wajar. Data milik TomTom, dipakai untuk keperluan
> akademik.
