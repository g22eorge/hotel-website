# Deployment Guide — Latitude Zero CMS

This app is a **Flask website + admin CMS**. For the admin and live editing to
work, the Flask app must **be** the public site (the frontend calls same-origin
`/api/…`). A static-only host (plain Netlify) cannot provide the admin.

Deploy the **`production`** branch. It contains the newest frontend **and** the
hardened backend.

---

## 0. Prerequisites (you already have these)

- A private domain you can edit DNS for
- A managed **Postgres** database (this is what makes data survive redeploys)
- A **Cloudinary** account (for uploading pictures from the admin)
- A Python host (Render, Railway, Fly.io, or a VPS)

---

## 1. Environment variables (set these on the host)

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | ✅ | `openssl rand -hex 32` — app refuses to boot without it |
| `ADMIN_USERNAME` | ✅ | seeds the first admin on first boot (e.g. `admin`) |
| `ADMIN_PASSWORD` | ✅ | strong password — used only to create the first admin |
| `DATABASE_URL` | ✅ | Postgres connection string. **Without this, data is lost on redeploy.** |
| `CLOUDINARY_CLOUD_NAME` | ✅ | from Cloudinary dashboard |
| `CLOUDINARY_API_KEY` | ✅ | from Cloudinary dashboard |
| `CLOUDINARY_API_SECRET` | ✅ | from Cloudinary dashboard |
| `COOKIE_SECURE` | ✅ | `true` in production (HTTPS). `false` only for local http. |
| `LOGIN_MAX_FAILS` | optional | default 8 |
| `LOGIN_LOCK_SECONDS` | optional | default 300 |

See `.env.example` for a copy-paste template.

**Start command (all hosts):**
```
gunicorn --preload -w 4 -b 0.0.0.0:$PORT app:app
```
`--preload` is required: it runs the one-time DB setup in the master process
before workers fork, avoiding a "table already exists" race on a fresh database.

---

## 2A. Deploy on Render (matches `render.yaml`)

1. Push this branch to GitHub (see §3).
2. Render → **New → Blueprint** → pick the repo → it reads `render.yaml`
   (creates the web service **and** a managed Postgres, wiring `DATABASE_URL`).
3. Fill the `sync: false` secrets when prompted: `ADMIN_USERNAME`,
   `ADMIN_PASSWORD`, and the three `CLOUDINARY_*` values.
4. Deploy. First boot creates tables + seeds default content and the admin user.

## 2B. Deploy on Railway (you already have an account)

1. Railway project → **Add Postgres** (gives `DATABASE_URL` in the service vars).
2. Deploy this repo/branch. Railway auto-detects Python from `requirements.txt`.
3. Set **Start Command** to the gunicorn line above (Settings → Deploy).
4. Add all env vars from §1 (reference `${{Postgres.DATABASE_URL}}` for the DB).
5. Deploy.

> Either way: **`DATABASE_URL` must point at Postgres, not the host's local disk.**
> On ephemeral filesystems SQLite is wiped on every redeploy.

---

## 3. Push the branch

```bash
git push -u origin production
```

Point the host at the **`production`** branch (or merge it into `main` and deploy
`main` — your call).

---

## 4. Connect your private domain

1. In the host's dashboard: **Settings → Custom Domain →** add `yourdomain.com`.
2. The host shows a target (a `CNAME` value, or `A`/`AAAA` records).
3. At your DNS provider, add that record for the domain/subdomain.
4. Wait for DNS + automatic HTTPS certificate (minutes to a few hours).
5. Confirm `COOKIE_SECURE=true` so the login cookie is only sent over HTTPS.

---

## 5. Post-deploy smoke test

- [ ] `https://yourdomain.com/` — homepage loads
- [ ] `https://yourdomain.com/admin/login/` — real login form (not a placeholder)
- [ ] Log in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`
- [ ] Content → Settings → change hero title → **Save** → refresh homepage → it changed
- [ ] Content → Rooms / Gallery → upload an image → it appears (confirms Cloudinary)
- [ ] Submit a booking on the site → shows under **Bookings**
- [ ] Redeploy the service, log back in → **your edits are still there** (confirms Postgres)
- [ ] Change the admin password (Users page) after first login

---

## 6. Notes

- The old `https://latitudezero.up.railway.app` currently serves a **static**
  build with a dead-end admin link — retire it or redeploy it from `production`.
- `admin/config.yml` + `netlify/` are legacy Decap/Netlify CMS files; harmless,
  unused by the Flask app. Safe to delete later.
- Back up: export bookings from **Bookings → Export**, and take periodic Postgres
  snapshots via your host.
