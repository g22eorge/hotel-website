document.addEventListener('DOMContentLoaded', function() {
    // Navbar scroll effect
    var navbar = document.getElementById('navbar');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Hamburger menu
    var hamburger = document.getElementById('hamburger');
    var navLinks = document.getElementById('navLinks');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('active');
        });

        // Close menu on link click
        navLinks.querySelectorAll('a').forEach(function(link) {
            link.addEventListener('click', function() {
                hamburger.classList.remove('active');
                navLinks.classList.remove('active');
            });
        });
    }

    // Smooth scroll for internal links
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Hero background carousel with Ken Burns effect
    var heroSlides = document.querySelectorAll('.hero-carousel-slide');
    if (heroSlides.length > 0) {
        var currentBg = 0;
        setInterval(function() {
            heroSlides[currentBg].classList.remove('active');
            currentBg = (currentBg + 1) % heroSlides.length;
            heroSlides[currentBg].classList.add('active');
        }, 5000);
    }

    // Hero image slider
    var heroImages = document.querySelectorAll('.hero-image-slider img');
    var heroDots = document.querySelectorAll('.hero-slider-dot');
    if (heroImages.length > 0) {
        var currentSlide = 0;

        function showHeroSlide(index) {
            heroImages.forEach(function(img) { img.classList.remove('active'); });
            heroDots.forEach(function(dot) { dot.classList.remove('active'); });
            heroImages[index].classList.add('active');
            if (heroDots[index]) heroDots[index].classList.add('active');
            currentSlide = index;
        }

        heroDots.forEach(function(dot) {
            dot.addEventListener('click', function() {
                showHeroSlide(parseInt(this.getAttribute('data-index')));
            });
        });

        setInterval(function() {
            var next = (currentSlide + 1) % heroImages.length;
            showHeroSlide(next);
        }, 4000);
    }

    // Gallery lightbox
    var galleryItems = document.querySelectorAll('.gallery-item');
    var lightbox = document.getElementById('lightbox');

    if (lightbox && galleryItems.length > 0) {
        var lightboxImg = lightbox.querySelector('.lightbox-content img');
        var lightboxClose = lightbox.querySelector('.lightbox-close');
        var lightboxPrev = lightbox.querySelector('.lightbox-prev');
        var lightboxNext = lightbox.querySelector('.lightbox-next');
        var currentLightbox = 0;
        var gallerySrcs = [];

        galleryItems.forEach(function(item, index) {
            var img = item.querySelector('img');
            if (img) {
                gallerySrcs.push(img.src);
                item.addEventListener('click', function() {
                    currentLightbox = index;
                    if (lightboxImg) lightboxImg.src = gallerySrcs[currentLightbox];
                    lightbox.classList.add('active');
                    document.body.style.overflow = 'hidden';
                });
            }
        });

        if (lightboxClose) {
            lightboxClose.addEventListener('click', closeLightbox);
        }

        if (lightboxPrev) {
            lightboxPrev.addEventListener('click', function() {
                currentLightbox = (currentLightbox - 1 + gallerySrcs.length) % gallerySrcs.length;
                if (lightboxImg) lightboxImg.src = gallerySrcs[currentLightbox];
            });
        }

        if (lightboxNext) {
            lightboxNext.addEventListener('click', function() {
                currentLightbox = (currentLightbox + 1) % gallerySrcs.length;
                if (lightboxImg) lightboxImg.src = gallerySrcs[currentLightbox];
            });
        }

        // Close on background click
        lightbox.addEventListener('click', function(e) {
            if (e.target === lightbox) {
                closeLightbox();
            }
        });

        function closeLightbox() {
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        }

        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            if (!lightbox.classList.contains('active')) return;
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowLeft' && lightboxPrev) lightboxPrev.click();
            if (e.key === 'ArrowRight' && lightboxNext) lightboxNext.click();
        });
    }

    // Intersection Observer for fade-in animations
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.section').forEach(function(section) {
        observer.observe(section);
    });
});
