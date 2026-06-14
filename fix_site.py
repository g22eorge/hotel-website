import os

BASE = '/Users/mac/hotel-website'
PAGES_DIR = os.path.join(BASE, 'pages')

def main():
    # 1. Update CSS to add padding-top to .page-hero
    css_path = os.path.join(BASE, 'styles.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()
    
    if 'padding-top: 80px' not in css:
        css = css.replace(
            '.page-hero {\n    height: 50vh;',
            '.page-hero {\n    padding-top: 80px;\n    height: 50vh;'
        )
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css)
        print('Updated styles.css')
    else:
        print('styles.css already has padding-top')

    # 2. Add hero to each page
    heroes = {
        'about.html': ('About Us', '../images/IMG_3388.jpeg'),
        'accommodation.html': ('Our Rooms & Cottages', '../images/IMG_3384.jpeg'),
        'contact.html': ('Contact Us', '../images/IMG_3389.jpeg'),
        'dining.html': ('Dining', '../images/IMG_3383.jpeg'),
        'gallery.html': ('Gallery', '../images/IMG_3387.jpeg'),
        'safari.html': ('Safari & Nature', '../images/IMG_3386.jpeg'),
        'services.html': ('Our Services', '../images/IMG_3391.jpeg'),
    }

    for filename, (hero_title, bg) in heroes.items():
        path = os.path.join(PAGES_DIR, filename)
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()

        if '<!-- Page Hero -->' in html:
            print(f'Skipping {filename}, hero already present')
            continue

        hero_section = f'''    <!-- Page Hero -->
    <section class="page-hero" style="background: linear-gradient(rgba(0,0,0,0.5),rgba(0,0,0,0.5)), url('{bg}') center/cover;">
        <div class="page-hero-overlay"></div>
        <div class="page-hero-content">
            <h1>{hero_title}</h1>
        </div>
    </section>'''

        # Inject hero after closing </nav> tag
        html = html.replace('</nav>', f'</nav>\n{hero_section}', 1)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'Updated {filename}')

if __name__ == '__main__':
    main()
