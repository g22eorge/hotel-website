
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

    // Booking form WhatsApp + Netlify handler
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

            // Send to Netlify Forms (email notification)
            var params = new URLSearchParams();
            data.forEach(function(value, key) {
                params.append(key, value);
            });

            fetch(window.location.pathname, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: params.toString()
            }).then(function(response) {
                console.log('Netlify form submitted', response.status);
            }).catch(function(err) {
                console.error('Netlify form error:', err);
            });

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
