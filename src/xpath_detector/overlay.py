"""JavaScript overlay injected in the page for click capture."""

OVERLAY_JS = r"""
(function () {
    if (window.__xpath_detector_installed) return;
    window.__xpath_detector_installed = true;

    const style = document.createElement('style');
    style.textContent = `
        .__xpath_detector_highlight {
            outline: 2px solid red !important;
            outline-offset: 2px !important;
            cursor: crosshair !important;
        }
        .__xpath_detector_tooltip {
            position: fixed;
            background: #222;
            color: #fff;
            padding: 4px 8px;
            font: 12px monospace;
            border-radius: 4px;
            pointer-events: none;
            z-index: 2147483647;
        }
    `;
    document.head.appendChild(style);

    let current = null;
    let tooltip = null;
    let active = true;

    function showTooltip(text, x, y) {
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.className = '__xpath_detector_tooltip';
            document.body.appendChild(tooltip);
        }
        tooltip.textContent = text;
        tooltip.style.left = (x + 10) + 'px';
        tooltip.style.top = (y + 10) + 'px';
    }

    function hideTooltip() {
        if (tooltip) tooltip.style.display = 'none';
    }

    document.addEventListener('mousemove', (e) => {
        if (!active) return;
        const el = document.elementFromPoint(e.clientX, e.clientY);
        if (!el || el === current) return;
        if (current) current.classList.remove('__xpath_detector_highlight');
        current = el;
        current.classList.add('__xpath_detector_highlight');
        if (tooltip) tooltip.style.display = 'block';
        showTooltip(el.tagName.toLowerCase() + (el.id ? '#' + el.id : ''), e.clientX, e.clientY);
    }, true);

    document.addEventListener('click', (e) => {
        if (!active) return;
        if (!(e.ctrlKey || e.metaKey)) return;
        e.preventDefault();
        e.stopPropagation();
        const el = e.target;
        const attrs = {};
        for (const a of el.attributes) attrs[a.name] = a.value;
        const data = {
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || '').trim().slice(0, 200),
            attributes: attrs,
            absolute_xpath: getAbsoluteXPath(el),
            is_visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
            is_enabled: !el.disabled,
        };
        console.log('__XPATH_CAPTURE__' + JSON.stringify(data));
    }, true);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            active = !active;
            if (!active && current) current.classList.remove('__xpath_detector_highlight');
            hideTooltip();
        }
    });

    function getAbsoluteXPath(el) {
        if (el.id) return '//*[@id="' + el.id + '"]';
        if (el === document.body) return '/html/body';
        let ix = 0;
        const siblings = el.parentNode ? el.parentNode.childNodes : [];
        for (const sibling of siblings) {
            if (sibling === el) {
                return getAbsoluteXPath(el.parentNode) + '/' + el.tagName.toLowerCase() + '[' + (ix + 1) + ']';
            }
            if (sibling.nodeType === 1 && sibling.tagName === el.tagName) ix++;
        }
        return '';
    }
})();
"""
