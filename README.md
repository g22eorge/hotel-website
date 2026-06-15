# Latitude Zero Cottages — Website & CMS

> **Status:** Ready for client handover. All website content is editable through the admin panel without touching any code.

---

## 1. What is this?

This is a complete website for **Latitude Zero Cottages Kikorongo** with a built-in content management system (CMS). You can manage every piece of text, image, and SEO data from the admin panel — no developer needed.

---

## 2. Quick Start

### Access the Admin Panel
```
http://localhost:5001/admin/
```

**Login credentials:**
- **Username:** `admin`
- **Password:** `latitude2026`

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

## 7. Important Reminders

| Tip | Details |
|-----|---------|
| **Always click Save Changes** after editing |
| **Only heroes and intro sections have image upload** | Other sections do not support images |
| **Image files** | Stored in `images/uploads/` — do not delete from disk manually |
| **Database** | `latitude_zero.db` — keep backups regularly |
| **Sort order** | In gallery and testimonials, lower numbers appear first. Use gaps (10, 20, 30) for easy insertion |
| **Icons** | Use FontAwesome 6 Free classes. Format: `fas fa-xxx` |
| **Passwords** | Change the admin password after handover from Users page |

---

## 8. If You Need a New Admin User

1. Log in as the superuser (`admin`)
2. Go to **Content → Users**
3. Click **Add New User**
4. Fill in the details and save

---

## 9. Technical Notes for Developer (if needed)

- **Framework:** Flask (Python 3)
- **Database:** SQLite (`latitude_zero.db`)
- **Server:** Runs on port 5001 by default
- **Startup:** `python3 app.py`
- **Environment:** Requires Python 3.10+, `pip3 install -r requirements.txt`

---

## 10. Support

For technical issues, code changes, or advanced customizations, contact the developer.
