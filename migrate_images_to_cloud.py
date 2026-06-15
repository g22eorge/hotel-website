#!/usr/bin/env python3
"""
Migrate local images to Cloudinary.
Run this ONCE after setting up Cloudinary env vars locally,
then push the updated database to Railway.

Usage:
    python migrate_images_to_cloud.py
"""
import os, glob

try:
    import cloudinary
    import cloudinary.uploader
except ImportError:
    print("Install cloudinary first: pip install cloudinary")
    exit(1)

# Must have env vars set
cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
api_key = os.environ.get('CLOUDINARY_API_KEY')
api_secret = os.environ.get('CLOUDINARY_API_SECRET')

if not all([cloud_name, api_key, api_secret]):
    print("Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET env vars first.")
    exit(1)

cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret
)

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
UPLOAD_FOLDER = 'latitude_zero'
url_map = {}  # local_path -> cloudinary_url


def upload_image(filepath, folder=UPLOAD_FOLDER):
    """Upload a single image to Cloudinary, return CDN URL."""
    filename = os.path.basename(filepath)
    result = cloudinary.uploader.upload(
        filepath,
        folder=folder,
        use_filename=True,
        unique_filename=True,
        resource_type='image'
    )
    return result['secure_url']


def scan_and_upload():
    """Scan images/ directory and upload all images."""
    print("Scanning images/ directory...")
    uploaded = []
    skipped = []

    for root, dirs, files in os.walk(IMAGES_DIR):
        for filename in files:
            if filename.startswith('.'):
                continue
            ext = filename.lower().split('.')[-1]
            if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, IMAGES_DIR)
            folder = os.path.dirname(rel_path).replace(os.sep, '/')

            # Determine Cloudinary subfolder
            if folder and folder != '.':
                cloud_folder = f"{UPLOAD_FOLDER}/{folder}"
            else:
                cloud_folder = UPLOAD_FOLDER

            # Avoid re-uploading if already exists (by checking if URL already cloudinary)
            # For new uploads, just upload
            print(f"  Uploading {rel_path} -> {cloud_folder}/")
            try:
                url = upload_image(filepath, cloud_folder)
                url_map[rel_path] = url
                uploaded.append((rel_path, url))
                print(f"    OK: {url}")
            except Exception as e:
                skipped.append((rel_path, str(e)))
                print(f"    FAIL: {e}")

    return uploaded, skipped


def update_database_url_map():
    """Update latitude_zero.db with new Cloudinary URLs for all matching images."""
    from app import app, db, Room, GalleryImage, SiteSettings, PageSection

    with app.app_context():
        updated = []

        # Rooms — check if image matches a local path
        rooms = Room.query.all()
        for room in rooms:
            if room.image and not room.image.startswith('http'):
                # Local image path like "images/IMG_3384.jpeg"
                rel = room.image.lstrip('/')
                if rel in url_map:
                    room.image = url_map[rel]
                    updated.append(f"Room '{room.name}': {rel} -> {url_map[rel]}")
                    print(f"  Updated Room '{room.name}': {room.image}")

        # Gallery images
        gallery_images = GalleryImage.query.all()
        for img in gallery_images:
            if img.image and not img.image.startswith('http'):
                rel = img.image.lstrip('/')
                if rel in url_map:
                    old = img.image
                    img.image = url_map[rel]
                    updated.append(f"Gallery: {rel} -> {url_map[rel]}")
                    print(f"  Updated Gallery image: {img.image}")

        # Site settings — hero image
        settings = SiteSettings.get_settings()
        if settings.hero_image and not settings.hero_image.startswith('http'):
            rel = settings.hero_image.lstrip('/')
            if rel in url_map:
                settings.hero_image = url_map[rel]
                updated.append(f"Hero: {rel} -> {url_map[rel]}")
                print(f"  Updated Hero image: {settings.hero_image}")

        # Page sections — hero and intro images
        sections = PageSection.query.filter(PageSection.image != '').all()
        for section in sections:
            if section.image and not section.image.startswith('http'):
                rel = section.image.lstrip('/')
                if rel in url_map:
                    section.image = url_map[rel]
                    updated.append(f"PageSection {section.page}/{section.section_key}: {rel} -> {url_map[rel]}")
                    print(f"  Updated PageSection {section.page}/{section.section_key}: {section.image}")

        db.session.commit()
        print(f"\nDatabase updated: {len(updated)} records changed")
        for u in updated:
            print(f"  {u}")


def main():
    print("=" * 60)
    print("IMAGE MIGRATION TO CLOUDINARY")
    print("=" * 60)
    print(f"Cloud name: {cloud_name}")
    print(f"Images dir: {IMAGES_DIR}")
    print()

    uploaded, skipped = scan_and_upload()

    print(f"\n{'='*60}")
    print(f"Upload complete: {len(uploaded)} uploaded, {len(skipped)} failed")

    if skipped:
        print("\nFailed uploads:")
        for s in skipped:
            print(f"  {s[0]}: {s[1]}")

    if uploaded:
        print(f"\n{'='*60}")
        print("Step 2: Update database with new URLs")
        update_database_url_map()

        print(f"\n{'='*60}")
        print(f"DONE — {len(uploaded)} images migrated to Cloudinary")
        print("Commit latitude_zero.db and push to Railway to apply in production.")
        print("Local images/ folder is no longer needed for uploaded content.")


if __name__ == '__main__':
    main()