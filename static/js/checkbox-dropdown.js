/**
 * Checkbox Dropdown
 * =================
 * Turns any <select multiple data-checkbox-dropdown> into a dropdown of
 * checkboxes — no Ctrl+click needed.
 *
 * The native <select> is kept in the DOM (visually hidden) and stays the
 * single source of truth: the form still submits its name, and existing
 * code reading `select.selectedOptions` keeps working unchanged.
 *
 * Markup:
 *   <select name="batch_ids" multiple data-checkbox-dropdown
 *           data-placeholder="انتخاب بچ..." data-search="1">
 *
 * Options:
 *   data-placeholder  text shown when nothing is selected
 *   data-search       "1" to always show the search box (default: when >8 options)
 *   data-size         "sm" for the compact variant
 */

(function () {
    'use strict';

    var SELECTOR = 'select[multiple][data-checkbox-dropdown]';

    function initDropdown(select) {
        if (select.dataset.cbdReady === '1') return;
        select.dataset.cbdReady = '1';

        var options = Array.prototype.slice.call(select.options);
        var placeholder = select.dataset.placeholder || 'انتخاب کنید...';
        var showSearch = select.dataset.search === '1' || options.length > 8;

        var wrap = document.createElement('div');
        wrap.className = 'cbd' + (select.dataset.size === 'sm' ? ' cbd-sm' : '');
        select.parentNode.insertBefore(wrap, select);
        wrap.appendChild(select);
        select.classList.add('cbd-native');
        select.removeAttribute('required');  // a hidden required control blocks submit in Chrome
        select.setAttribute('tabindex', '-1');
        select.setAttribute('aria-hidden', 'true');

        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'cbd-toggle';
        toggle.setAttribute('aria-haspopup', 'listbox');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.innerHTML = '<span class="cbd-label"></span><i class="bi bi-chevron-down cbd-caret"></i>';
        wrap.appendChild(toggle);

        var panel = document.createElement('div');
        panel.className = 'cbd-panel';
        wrap.appendChild(panel);

        var search = null;
        if (showSearch) {
            search = document.createElement('input');
            search.type = 'text';
            search.className = 'cbd-search';
            search.placeholder = 'جستجو...';
            panel.appendChild(search);
        }

        var actions = document.createElement('div');
        actions.className = 'cbd-actions';
        actions.innerHTML = '<button type="button" class="cbd-action" data-all>انتخاب همه</button>' +
                            '<button type="button" class="cbd-action" data-none>هیچ‌کدام</button>';
        panel.appendChild(actions);

        var list = document.createElement('div');
        list.className = 'cbd-list';
        panel.appendChild(list);

        var empty = document.createElement('div');
        empty.className = 'cbd-empty';
        empty.textContent = 'موردی یافت نشد';
        empty.style.display = 'none';
        panel.appendChild(empty);

        var rows = options.map(function (opt, i) {
            var row = document.createElement('label');
            row.className = 'cbd-option' + (opt.dataset.cbdExclusive === '1' ? ' cbd-option-exclusive' : '');

            var box = document.createElement('input');
            box.type = 'checkbox';
            box.className = 'form-check-input';
            box.checked = opt.selected;
            box.value = opt.value;

            var text = document.createElement('span');
            text.textContent = opt.textContent.trim();

            row.appendChild(box);
            row.appendChild(text);
            list.appendChild(row);

            box.addEventListener('change', function () {
                opt.selected = box.checked;
                if (box.checked) applyExclusive(opt.dataset.cbdExclusive === '1');
                select.dispatchEvent(new Event('change', { bubbles: true }));
                renderLabel();
            });

            return {
                row: row, box: box, opt: opt, text: text.textContent, index: i,
                exclusive: opt.dataset.cbdExclusive === '1'
            };
        });

        /**
         * An option marked data-cbd-exclusive="1" (e.g. "clear everything") can't
         * be combined with the normal ones — whichever side was just ticked wins.
         */
        function applyExclusive(exclusiveWasTicked) {
            rows.forEach(function (r) {
                if (r.exclusive === exclusiveWasTicked) return;
                if (!r.box.checked) return;
                r.box.checked = false;
                r.opt.selected = false;
            });
        }

        function renderLabel() {
            var label = toggle.querySelector('.cbd-label');
            var chosen = rows.filter(function (r) { return r.opt.selected; });
            label.innerHTML = '';

            if (!chosen.length) {
                var ph = document.createElement('span');
                ph.className = 'cbd-placeholder';
                ph.textContent = placeholder;
                label.appendChild(ph);
                return;
            }

            chosen.slice(0, 4).forEach(function (r) {
                var chip = document.createElement('span');
                chip.className = 'cbd-chip';

                var name = document.createElement('span');
                name.textContent = r.text;
                chip.appendChild(name);

                var x = document.createElement('button');
                x.type = 'button';
                x.className = 'cbd-chip-x';
                x.innerHTML = '&times;';
                x.title = 'حذف';
                x.addEventListener('click', function (e) {
                    e.stopPropagation();
                    r.box.checked = false;
                    r.box.dispatchEvent(new Event('change'));
                });
                chip.appendChild(x);
                label.appendChild(chip);
            });

            if (chosen.length > 4) {
                var more = document.createElement('span');
                more.className = 'cbd-placeholder';
                more.textContent = '+' + (chosen.length - 4) + ' مورد دیگر';
                label.appendChild(more);
            }
        }

        function setOpen(open) {
            wrap.classList.toggle('is-open', open);
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (!open) return;

            // Flip upwards when there isn't room below (long lists near the page bottom)
            wrap.classList.remove('drop-up');
            var room = window.innerHeight - toggle.getBoundingClientRect().bottom;
            if (room < panel.offsetHeight + 16) wrap.classList.add('drop-up');

            if (search) { search.value = ''; filter(''); search.focus(); }
        }

        function filter(term) {
            term = term.trim().toLowerCase();
            var visible = 0;
            rows.forEach(function (r) {
                var hit = !term || r.text.toLowerCase().indexOf(term) !== -1;
                r.row.classList.toggle('is-hidden', !hit);
                if (hit) visible++;
            });
            empty.style.display = visible ? 'none' : 'block';
        }

        function setAll(checked) {
            rows.forEach(function (r) {
                if (r.row.classList.contains('is-hidden')) return;  // respect the active search
                if (r.exclusive && checked) return;                 // never bulk-tick a sentinel option
                r.box.checked = checked;
                r.opt.selected = checked;
            });
            select.dispatchEvent(new Event('change', { bubbles: true }));
            renderLabel();
        }

        toggle.addEventListener('click', function () { setOpen(!wrap.classList.contains('is-open')); });
        if (search) search.addEventListener('input', function () { filter(search.value); });
        actions.querySelector('[data-all]').addEventListener('click', function () { setAll(true); });
        actions.querySelector('[data-none]').addEventListener('click', function () { setAll(false); });

        document.addEventListener('click', function (e) {
            if (!wrap.contains(e.target)) setOpen(false);
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && wrap.classList.contains('is-open')) { setOpen(false); toggle.focus(); }
        });

        // Let outside code push a new selection into the native select and refresh the UI
        select.addEventListener('cbd:sync', function () {
            rows.forEach(function (r) { r.box.checked = r.opt.selected; });
            renderLabel();
        });

        renderLabel();
    }

    function initAll(root) {
        (root || document).querySelectorAll(SELECTOR).forEach(initDropdown);
    }

    document.addEventListener('DOMContentLoaded', function () { initAll(); });
    window.initCheckboxDropdowns = initAll;
})();
