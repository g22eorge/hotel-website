# Latitude Zero Cottages — Website & CMS

> **Status:** Ready for client handover after Railway environment variables are set. The Flask admin panel is the source of truth for website content.

---

## 1. What is this?

This is a complete website for **Latitude Zero Cottages Kikorongo** with a built-in Flask content management system (CMS). You can manage every piece of text, image, and SEO data from the Flask admin panel — no developer needed.

The public pages read live content from the Flask APIs first. The JSON files in `data/` are kept as static fallback content only.

---

## 2. Quick Start

### Access the Admin Panel
```
https://latitudezero.up.railway.app/admin/
```

**Login credentials** (set these in Railway environment variables):
- **Username:** set `ADMIN_USERNAME` env var
- **Password:** set `ADMIN_PASSWORD` env var

*(Only superusers can create or delete other users.)*

---

## 3. Admin Panel Overview

| Section | What it controls |
|---------|------------------|
| **Dashboard** | Overview of bookings, recent activity |
| **Bookings** | View all guest bookings and details |
| **Users** | Manage admin users (superuser only) |
| **Content → Settings** | Edit hero image, contact info, social links, homepage SEO |
| **Content → Testimonials** | Add, edit, or remove guest reviews |
| **Content → Rooms** | Add, edit, or remove room listings |
| **Content → Gallery** | Upload, edit, or remove gallery images |
| **Content → Pages** | Edit page sections (hero, body text, feature items) |

---

## 4. Editing Content

### 4.1 Hero Section & Site-wide Info (Settings)

Go to **Content → Settings**.

Editable items:
- **Hero:** Title, subtitle, tagline, background image
- **Homepage SEO:** Page title and meta description
- **Contact:** WhatsApp, phone, email, address
- **Social:** Facebook, Instagram
- **Footer:** Tagline and copyright text

Click **Save Changes** at the bottom.

### 4.2 Per-Page Content (Pages)

Go to **Content → Pages**. You will see:
- `about` — About page
- `services` — Services page
- `gallery` — Gallery page
- `contact` — Contact page

Click any page name to edit its sections.

#### Page Sections
Each page has multiple sections (e.g., “hero”, “rooms”, “safari”). For each section you can edit:
- **Title** — the heading text
- **Content** — the body text
- **Image** — for hero and intro sections only
- **SEO** — for the hero section only (page title and meta description)

#### Feature Grids (Services & About)
For sections that show icon grids (Our Promise, Who We Serve, Safari, Amenities), a visual item builder is provided:

1. Type your **Intro Text** at the top.
2. Click **+ Add Item** to add a new feature row.
3. Each row has:
   - **Icon** — e.g. `fas fa-wifi` (FontAwesome class)
   - **Text** — the feature description
   - *For Amenities only: additional Description field*
4. Click **Remove** to delete a row.
5. Click **Save Changes** at the bottom.

> **Finding icons:** Visit [FontAwesome Free Icons](https://fontawesome.com/v6/search?m=free), click an icon, and copy the class (e.g. `fas fa-bed`).

### 4.3 Testimonials

Go to **Content → Testimonials**.

You can:
- Add a new testimonial (+ button)
- Edit existing ones (click the row)
- Deactivate / activate (toggle button)

**Fields:**
- Name / author
- Location
- Testimonial text
- Rating (1–5 stars)

### 4.4 Rooms

Go to **Content → Rooms**.

You can:
- Add new room types
- Edit name, description, price, image, features
- Disable rooms that are not currently available

### 4.5 Gallery

Go to **Content → Gallery**.

You can:
- Upload images (click **Add Image**)
- Set a caption / sort order
- Remove old images

**Important:** Order matters. Lower numbers appear first. Use sort numbers like 10, 20, 30 to leave room for future insertions.

---

## 5. SEO (Search Engine Optimization)

SEO data controls how your pages appear in Google search results.

### Homepage SEO
Go to **Content → Settings → Homepage SEO**:
- **Page Title (meta title)** — appears in Google as the main title
- **Meta Description** — appears under the title in Google results

### Subpage SEO
Go to **Content → Pages → [page]**:
- SEO settings appear **inside the hero section** only (`Section Title`, `Content`, then SEO fields)

---

## 6. Bookings

The website booking form sends guests to your WhatsApp and also saves the request in the database. You can view all bookings at **Bookings** in the sidebar.

---

## 7. Cloudinary Setup (Image Storage)

All uploaded images are stored in **Cloudinary** — a cloud image service. This ensures images survive server redeploys and load fast from a CDN.

### Setup (one-time)

1. Create a free Cloudinary account: https://cloudinary.com/users/register/free
2. Go to your **Dashboard** and copy:
   - Cloud Name
   - API Key
   - API Secret
3. Add these as environment variables on your hosting (e.g. Railway):

| Variable | Value |
|----------|-------|
| `CLOUDINARY_CLOUD_NAME` | your_cloud_name |
| `CLOUDINARY_API_KEY` | your_api_key |
| `CLOUDINARY_API_SECRET` | your_api_secret |

4. Redeploy your app — uploads will now go to Cloudinary.

### After Setup

- Any image you upload via the admin panel goes to Cloudinary
- Images are served globally via Cloudinary's CDN
- **Existing local images** (in the repo, e.g. `images/IMG_3384.jpeg`) continue to work — these are committed to git and served locally

---

## 8. Important Reminders

| Tip | Details |
|-----|---------|
| **Always click Save Changes** after editing |
| **Only heroes and intro sections have image upload** | Other sections do not support images |
| **Uploaded images** | Stored in Cloudinary (not local filesystem) |
| **Default images** | Repo images like `images/IMG_*.jpeg` are local — committed to git |
| **Database** | Use Railway PostgreSQL through `DATABASE_URL` in production; SQLite is the local fallback |
| **Sort order** | In gallery and testimonials, lower numbers appear first. Use gaps (10, 20, 30) for easy insertion |
| **Icons** | Use FontAwesome 6 Free classes. Format: `fas fa-xxx` |
| **Passwords** | Change the admin password via the Users page — set `ADMIN_PASSWORD` env var on Railway |

---

## 9. If You Need a New Admin User

1. Log in as the superuser (`admin`)
2. Go to **Content → Users**
3. Click **Add New User**
4. Fill in the details and save

---

## 10. Technical Notes for Developer (if needed)

- **Framework:** Flask (Python 3)
- **Database:** PostgreSQL via `DATABASE_URL` in production; SQLite (`latitude_zero.db`) locally
- **Image Storage:** Cloudinary (credentials via env vars)
- **WSGI Server:** gunicorn (production)
- **Startup (local):** `python3 app.py`
- **Startup (production):** `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`

### Railway Deployment

1. Connect your GitHub repo to Railway
2. Add these **Environment Variables** in Railway:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Generate a random 64-character secret (e.g. `openssl rand -hex 32`) |
| `ADMIN_USERNAME` | Your admin login username (e.g. `admin`) |
| `ADMIN_PASSWORD` | Your admin login password (keep this secret!) |
| `DATABASE_URL` | Railway PostgreSQL connection URL |
| `CLOUDINARY_CLOUD_NAME` | From your Cloudinary dashboard |
| `CLOUDINARY_API_KEY` | From your Cloudinary dashboard |
| `CLOUDINARY_API_SECRET` | From your Cloudinary dashboard |

3. **Start Command:** `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
4. Add a Railway PostgreSQL database and connect it to the service so `DATABASE_URL` is available.
5. On first startup, the app creates tables and seeds default content. If no admin user exists, it creates one using `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

### Keeping the Database Safe

Production should use Railway PostgreSQL, not Railway's local filesystem. To prevent data loss:
- Keep `DATABASE_URL` connected to a managed Railway PostgreSQL database
- Export bookings regularly from the admin panel (`/admin/bookings/` — use Export button)
- Use the local `latitude_zero.db` file only for development and fallback seed data

### Netlify / Static Fallback

Netlify can still serve the static pages and `data/*.json` fallback content, but it is not the live CMS target. The live admin is the Flask admin at `/admin/` on Railway.

---

## 11. Support

For technical issues, code changes, or advanced customizations, contact the developer.
