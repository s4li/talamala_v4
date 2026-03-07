/**
 * Price Input Enhancement
 * - Live comma separator (thousands) while typing
 * - Persian number-to-words display below input
 *
 * Usage: Add class "price-input" to any <input> and
 *        add a sibling <small class="price-words"></small> below it.
 *
 * Or call: initPriceInput(inputEl, wordsEl)
 */

// --- Number to Persian Words ---
function numberToWordsFa(num) {
    if (!num || num <= 0) return '';
    num = Math.floor(num);

    const yekan = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه'];
    const dahgan = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود'];
    const dahyek = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده'];
    const sadgan = ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد'];
    const scale = ['', 'هزار', 'میلیون', 'میلیارد', 'تریلیون'];

    function threeDigits(n) {
        if (n === 0) return '';
        let parts = [];
        let s = Math.floor(n / 100);
        let d = Math.floor((n % 100) / 10);
        let y = n % 10;
        if (s > 0) parts.push(sadgan[s]);
        if (d === 1) {
            parts.push(dahyek[y]);
            return parts.join(' و ');
        }
        if (d > 1) parts.push(dahgan[d]);
        if (y > 0) parts.push(yekan[y]);
        return parts.join(' و ');
    }

    let chunks = [];
    let i = 0;
    while (num > 0) {
        let rem = num % 1000;
        if (rem > 0) {
            let w = threeDigits(rem);
            if (scale[i]) w += ' ' + scale[i];
            chunks.unshift(w);
        }
        num = Math.floor(num / 1000);
        i++;
    }
    return chunks.join(' و ');
}

// --- Format number with comma separator ---
function formatWithCommas(val) {
    return val.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// --- Init a single price input ---
function initPriceInput(input, wordsEl) {
    // Change type from number to text for comma formatting
    input.type = 'text';
    input.inputMode = 'numeric';
    input.autocomplete = 'off';

    // Store the hidden input for form submission (raw number)
    let hiddenName = input.name;
    let hidden = document.createElement('input');
    hidden.type = 'hidden';
    hidden.name = hiddenName;
    input.name = ''; // Remove name from visible input
    input.parentNode.insertBefore(hidden, input.nextSibling);

    function getRawValue() {
        return parseInt(input.value.replace(/[^0-9]/g, '')) || 0;
    }

    function update() {
        let raw = getRawValue();
        hidden.value = raw;

        // Format with commas
        let cursorPos = input.selectionStart;
        let oldLen = input.value.length;
        input.value = raw > 0 ? formatWithCommas(raw) : '';
        let newLen = input.value.length;
        // Adjust cursor position
        let newPos = cursorPos + (newLen - oldLen);
        if (newPos < 0) newPos = 0;
        input.setSelectionRange(newPos, newPos);

        // Update words
        if (wordsEl) {
            if (raw > 0) {
                wordsEl.innerHTML = '<i class="bi bi-info-circle me-1"></i>' + numberToWordsFa(raw) + ' تومان';
                wordsEl.style.display = '';
            } else {
                wordsEl.textContent = '';
                wordsEl.style.display = 'none';
            }
        }
    }

    input.addEventListener('input', update);

    // Initial format (if value already set)
    let initVal = parseInt(input.value.replace(/[^0-9]/g, '')) || 0;
    if (initVal > 0) {
        hidden.value = initVal;
        input.value = formatWithCommas(initVal);
        if (wordsEl) {
            wordsEl.innerHTML = '<i class="bi bi-info-circle me-1"></i>' + numberToWordsFa(initVal) + ' تومان';
        }
    } else {
        hidden.value = '0';
    }
}

// --- Auto-init all .price-input elements ---
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.price-input').forEach(function(input) {
        // Find or create words element
        let wordsEl = input.parentElement.querySelector('.price-words');
        if (!wordsEl) {
            // Look in parent's parent (for input-group)
            let container = input.closest('.mb-3') || input.closest('.col-md-6') || input.closest('.col-5') || input.parentElement.parentElement;
            wordsEl = container ? container.querySelector('.price-words') : null;
        }
        initPriceInput(input, wordsEl);
    });
});
