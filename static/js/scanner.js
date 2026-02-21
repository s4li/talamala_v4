/**
 * TmScanner — Barcode / QR Scanner Wrapper
 * ==========================================
 * Supports: Camera (html5-qrcode), USB barcode scanner (keyboard emulation).
 * Usage:
 *   TmScanner.init({ containerId: 'scanner-area', onScan: fn, onError: fn });
 *   TmScanner.startCamera();
 *   TmScanner.stopCamera();
 */
const TmScanner = (() => {
    let _html5Qr = null;
    let _onScan = null;
    let _onError = null;
    let _containerId = null;
    let _cameraRunning = false;
    let _lastScanTime = 0;
    const COOLDOWN_MS = 2000; // Prevent double-reads

    // --- USB Scanner Keyboard Listener ---
    let _keyBuffer = '';
    let _keyTimer = null;
    const KEY_TIMEOUT = 200; // ms — USB scanners type fast

    function _handleKeydown(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        if (e.key === 'Enter' && _keyBuffer.length >= 4) {
            e.preventDefault();
            _processCode(_keyBuffer.trim());
            _keyBuffer = '';
            clearTimeout(_keyTimer);
            return;
        }

        if (e.key.length === 1) {
            _keyBuffer += e.key;
            clearTimeout(_keyTimer);
            _keyTimer = setTimeout(() => { _keyBuffer = ''; }, KEY_TIMEOUT);
        }
    }

    function _processCode(raw) {
        const now = Date.now();
        if (now - _lastScanTime < COOLDOWN_MS) return;
        _lastScanTime = now;

        // Extract serial from URL patterns like ?code=XXXX or ?serial=XXXX
        let code = raw;
        try {
            if (raw.startsWith('http')) {
                const url = new URL(raw);
                code = url.searchParams.get('code')
                    || url.searchParams.get('serial')
                    || url.pathname.split('/').pop()
                    || raw;
            }
        } catch (_) { /* not a URL, use raw */ }

        code = code.toUpperCase().trim();
        if (code && _onScan) _onScan(code);
    }

    return {
        init({ containerId, onScan, onError }) {
            _containerId = containerId;
            _onScan = onScan;
            _onError = onError || console.error;

            // Start USB listener
            document.removeEventListener('keydown', _handleKeydown);
            document.addEventListener('keydown', _handleKeydown);
        },

        async startCamera() {
            if (_cameraRunning) return;
            if (!window.Html5Qrcode) {
                _onError && _onError('html5-qrcode library not loaded');
                return;
            }

            _html5Qr = new Html5Qrcode(_containerId);
            try {
                await _html5Qr.start(
                    { facingMode: 'environment' },
                    { fps: 10, qrbox: { width: 250, height: 250 } },
                    (decodedText) => _processCode(decodedText),
                    () => {} // ignore scan failures
                );
                _cameraRunning = true;
            } catch (err) {
                _onError && _onError(err.message || err);
            }
        },

        async stopCamera() {
            if (!_cameraRunning || !_html5Qr) return;
            try {
                await _html5Qr.stop();
                _html5Qr.clear();
            } catch (_) {}
            _cameraRunning = false;
        },

        isCameraRunning() {
            return _cameraRunning;
        },

        destroy() {
            this.stopCamera();
            document.removeEventListener('keydown', _handleKeydown);
        }
    };
})();
