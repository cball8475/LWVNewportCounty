/* LWV Newport County: shared page script, loaded by every page.
   Runs the phone/tablet menu button in the main nav (.site-nav):
   - the button's aria-expanded tells screen readers whether the menu is open
   - Escape closes the menu and returns focus to the button
   - tapping outside the nav closes it
   - widening the window to the full desktop nav closes it
   The 1180px width must match the max-width: 1179px breakpoint in styles.css. */
(function () {
    var toggle = document.querySelector('.site-nav__toggle');
    var menu = document.getElementById('site-menu');
    if (!toggle || !menu) return;

    function isOpen() {
        return toggle.getAttribute('aria-expanded') === 'true';
    }

    function setOpen(open) {
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        menu.classList.toggle('is-open', open);
    }

    toggle.addEventListener('click', function () {
        setOpen(!isOpen());
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && isOpen()) {
            setOpen(false);
            toggle.focus();
        }
    });

    document.addEventListener('click', function (e) {
        if (isOpen() && !e.target.closest('.site-nav')) setOpen(false);
    });

    // Following an in-page link (e.g. #donate) closes the menu
    menu.addEventListener('click', function (e) {
        if (e.target.closest('a')) setOpen(false);
    });

    var desktop = window.matchMedia('(min-width: 1180px)');
    var onChange = function (e) { if (e.matches) setOpen(false); };
    if (desktop.addEventListener) desktop.addEventListener('change', onChange);
    else if (desktop.addListener) desktop.addListener(onChange);
})();
