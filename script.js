
document.addEventListener('DOMContentLoaded', function() {
    // Scroll-triggered fade-in animations
    document.querySelectorAll('.section, .section-header, .cards-grid, .rooms-section-grid, .testimonial-card, .room-preview-card, .dining-card, .footer-grid').forEach(function(el) {
        el.classList.add('fade-section', 'fade-prepare');
    });
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.fade-section').forEach(function(el) {
        observer.observe(el);
    });

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

    // Gallery lightbox with zoom and fullscreen
    var galleryItems = document.querySelectorAll('.gallery-item');
    var lightbox = document.getElementById('lightbox');

    if (lightbox && galleryItems.length > 0) {
        var lightboxImg = document.getElementById('lightboxImg');
        var lightboxClose = document.getElementById('lightboxCloseBtn');
        var lightboxPrev = document.getElementById('lightboxPrev');
        var lightboxNext = document.getElementById('lightboxNext');
        var lightboxContent = document.getElementById('lightboxContent');
        var lightboxCaption = document.getElementById('lightboxCaption');
        var lightboxCounter = document.getElementById('lightboxCounter');
        var currentLightbox = 0;
        var gallerySrcs = [];
        var galleryCaptions = [];
        var zoomLevel = 1;
        var panX = 0, panY = 0;
        var isDragging = false;
        var startX = 0, startY = 0;
        var isPanning = false;

        galleryItems.forEach(function(item, index) {
            var img = item.querySelector('img');
            if (img) {
                gallerySrcs.push(img.src);
                var captionEl = item.querySelector('.gallery-caption');
                galleryCaptions.push(captionEl ? captionEl.textContent.trim() : '');
                item.addEventListener('click', function() {
                    openLightbox(index);
                });
            }
        });

        function openLightbox(index) {
            currentLightbox = index;
            zoomLevel = 1;
            panX = 0;
            panY = 0;
            applyTransform();
            if (lightboxImg) lightboxImg.src = gallerySrcs[currentLightbox];
            if (lightboxCaption) lightboxCaption.textContent = galleryCaptions[currentLightbox] || '';
            if (lightboxCounter) lightboxCounter.textContent = (currentLightbox + 1) + ' / ' + gallerySrcs.length;
            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeLightbox() {
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
            zoomLevel = 1;
            panX = 0;
            panY = 0;
        }

        function applyTransform() {
            if (!lightboxImg) return;
            var tx = 'scale(' + zoomLevel + ') translate(' + panX + 'px, ' + panY + 'px)';
            lightboxImg.style.transform = tx;
            lightboxContent.classList.toggle('zoomed', zoomLevel > 1);
        }

        if (lightboxClose) lightboxClose.addEventListener('click', closeLightbox);

        if (lightboxPrev) {
            lightboxPrev.addEventListener('click', function() {
                currentLightbox = (currentLightbox - 1 + gallerySrcs.length) % gallerySrcs.length;
                zoomLevel = 1; panX = 0; panY = 0;
                openLightbox(currentLightbox);
            });
        }

        if (lightboxNext) {
            lightboxNext.addEventListener('click', function() {
                currentLightbox = (currentLightbox + 1) % gallerySrcs.length;
                zoomLevel = 1; panX = 0; panY = 0;
                openLightbox(currentLightbox);
            });
        }

        // Zoom controls
        var zoomInBtn = document.getElementById('lightboxZoomIn');
        var zoomOutBtn = document.getElementById('lightboxZoomOut');
        var fullscreenBtn = document.getElementById('lightboxFullscreen');

        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', function() {
                zoomLevel = Math.min(zoomLevel + 0.5, 4);
                applyTransform();
            });
        }

        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', function() {
                zoomLevel = Math.max(zoomLevel - 0.5, 1);
                if (zoomLevel === 1) { panX = 0; panY = 0; }
                applyTransform();
            });
        }

        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', function() {
                if (!document.fullscreenElement) {
                    lightbox.requestFullscreen ? lightbox.requestFullscreen() : lightbox.webkitRequestFullscreen();
                    fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>';
                    fullscreenBtn.title = 'Exit full screen';
                } else {
                    document.exitFullscreen ? document.exitFullscreen() : document.webkitExitFullscreen();
                    fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
                    fullscreenBtn.title = 'Full screen';
                }
            });
        }

        document.addEventListener('fullscreenchange', function() {
            if (!document.fullscreenElement && fullscreenBtn) {
                fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
                fullscreenBtn.title = 'Full screen';
            }
        });

        // Mouse wheel zoom
        lightbox.addEventListener('wheel', function(e) {
            e.preventDefault();
            if (e.deltaY < 0) zoomLevel = Math.min(zoomLevel + 0.15, 4);
            else zoomLevel = Math.max(zoomLevel - 0.15, 1);
            if (zoomLevel === 1) { panX = 0; panY = 0; }
            applyTransform();
        }, { passive: false });

        // Drag to pan when zoomed
        lightboxContent.addEventListener('mousedown', function(e) {
            if (zoomLevel <= 1) return;
            isDragging = true;
            startX = e.clientX - panX;
            startY = e.clientY - panY;
            lightboxContent.style.cursor = 'grabbing';
        });

        document.addEventListener('mousemove', function(e) {
            if (!isDragging || zoomLevel <= 1) return;
            isPanning = true;
            panX = e.clientX - startX;
            panY = e.clientY - startY;
            applyTransform();
        });

        document.addEventListener('mouseup', function() {
            isDragging = false;
            setTimeout(function() { isPanning = false; }, 50);
            if (lightboxContent) lightboxContent.style.cursor = 'grab';
        });

        // Click on image to zoom in (when not dragging)
        lightboxContent.addEventListener('click', function(e) {
            if (isPanning) return;
            if (zoomLevel > 1) { zoomLevel = 1; panX = 0; panY = 0; applyTransform(); }
            else { zoomLevel = 2; applyTransform(); }
        });

        // Close on background click
        lightbox.addEventListener('click', function(e) {
            if (e.target === lightbox) closeLightbox();
        });

        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            if (!lightbox.classList.contains('active')) return;
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowLeft') lightboxPrev && lightboxPrev.click();
            if (e.key === 'ArrowRight') lightboxNext && lightboxNext.click();
            if (e.key === '+' || e.key === '=') { zoomLevel = Math.min(zoomLevel + 0.5, 4); applyTransform(); }
            if (e.key === '-') { zoomLevel = Math.max(zoomLevel - 0.5, 1); if (zoomLevel === 1) { panX = 0; panY = 0; } applyTransform(); }
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

    // Booking form WhatsApp handler
    function handleBookingForm(formEl) {
        if (!formEl) return;
        formEl.addEventListener('submit', function(e) {
            e.preventDefault();
            var data = new FormData(formEl);
            var fields = {};
            data.forEach(function(value, key) {
                fields[key] = value;
            });

            var msg = 'Hello Latitude Zero Cottages! I would like to make a booking:\n\n';
            if (fields.checkin) msg += 'Check-in: ' + fields.checkin + '\n';
            if (fields.checkout) msg += 'Check-out: ' + fields.checkout + '\n';
            if (fields.guests) msg += 'Guests: ' + fields.guests + '\n';
            if (fields.room) msg += 'Room: ' + fields.room + '\n';
            if (fields.name) msg += 'Name: ' + fields.name + '\n';
            if (fields.email) msg += 'Email: ' + fields.email + '\n';
            if (fields.phone) msg += 'Phone: ' + fields.phone + '\n';
            if (fields.requests) msg += 'Requests: ' + fields.requests + '\n';

            var waNumber = window.WHATSAPP_NUMBER || '256700629083';
            var waUrl = 'https://wa.me/' + waNumber + '?text=' + encodeURIComponent(msg);
            window.open(waUrl, '_blank');
        });
    }

    handleBookingForm(document.getElementById('homepageBookingForm'));
    handleBookingForm(document.getElementById('contactBookingForm'));

    // Set min date for booking date inputs to today
    var today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(function(input) {
        input.setAttribute('min', today);
    });

    // Sticky booking bar (scroll-triggered)
    var bookingBar = document.getElementById('stickyBookingBar');
    if (bookingBar) {
        var closedAt = localStorage.getItem('bookingBarClosed');
        if (!closedAt || (Date.now() - parseInt(closedAt)) > 24 * 60 * 60 * 1000) {
            var shown = false;
            function revealBar() {
                if (shown) return;
                bookingBar.classList.add('visible');
                shown = true;
            }
            var onScroll = function() {
                if (window.scrollY > 100) {
                    revealBar();
                    window.removeEventListener('scroll', onScroll);
                }
            };
            window.addEventListener('scroll', onScroll);

            var closeBtn = bookingBar.querySelector('.bar-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    bookingBar.classList.remove('visible');
                    localStorage.setItem('bookingBarClosed', Date.now());
                    window.removeEventListener('scroll', onScroll);
                });
            }
        }
    }
});
