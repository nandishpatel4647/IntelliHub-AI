/* ============================================================
   IntelliHub AI — Global JavaScript
   Intelligent Data Analytics & Machine Learning Platform
   ============================================================ */

(function () {
    'use strict';

    /* ── Cookie Helper ──────────────────────────────────────── */

    /**
     * Retrieve a cookie value by name.
     * @param {string} name - The cookie name.
     * @returns {string|null} The cookie value or null.
     */
    function getCookie(name) {
        if (!document.cookie || document.cookie === '') {
            return null;
        }
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + '=') {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        return null;
    }

    /* ── Debounce Utility ───────────────────────────────────── */

    /**
     * Returns a debounced version of the given function.
     * @param {Function} func - The function to debounce.
     * @param {number} [wait=300] - Delay in milliseconds.
     * @returns {Function} Debounced function.
     */
    function debounce(func, wait) {
        if (typeof wait === 'undefined') { wait = 300; }
        var timeout;
        return function () {
            var context = this;
            var args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function () {
                func.apply(context, args);
            }, wait);
        };
    }

    /* ── Format Numbers ─────────────────────────────────────── */

    /**
     * Format a number with comma separators.
     * @param {number} num - The number to format.
     * @returns {string} Formatted string (e.g. 1,000).
     */
    function formatNumber(num) {
        if (num === null || typeof num === 'undefined') return '0';
        return Number(num).toLocaleString('en-US');
    }

    /**
     * Convert bytes to a human-readable file size string.
     * @param {number} bytes - Size in bytes.
     * @returns {string} Formatted size (e.g. "1.5 MB").
     */
    function formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        var units = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        var i = Math.floor(Math.log(bytes) / Math.log(1024));
        if (i >= units.length) i = units.length - 1;
        var size = bytes / Math.pow(1024, i);
        return size.toFixed(i === 0 ? 0 : 2) + ' ' + units[i];
    }

    /* ── Count-Up Animation ─────────────────────────────────── */

    /**
     * Animate a number element from 0 to a target value.
     * @param {HTMLElement} element - The DOM element to animate.
     * @param {number} target - The final number.
     * @param {number} [duration=2000] - Animation duration in ms.
     */
    function animateCountUp(element, target, duration) {
        if (typeof duration === 'undefined') { duration = 2000; }
        var start = 0;
        var startTime = null;
        var isFloat = target % 1 !== 0;
        var suffix = element.getAttribute('data-suffix') || '';
        var prefix = element.getAttribute('data-prefix') || '';

        function easeOutQuart(t) {
            return 1 - Math.pow(1 - t, 4);
        }

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var elapsed = timestamp - startTime;
            var progress = Math.min(elapsed / duration, 1);
            var easedProgress = easeOutQuart(progress);
            var current = start + (target - start) * easedProgress;

            if (isFloat) {
                element.textContent = prefix + current.toFixed(1) + suffix;
            } else {
                element.textContent = prefix + formatNumber(Math.floor(current)) + suffix;
            }

            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                if (isFloat) {
                    element.textContent = prefix + target.toFixed(1) + suffix;
                } else {
                    element.textContent = prefix + formatNumber(target) + suffix;
                }
            }
        }

        requestAnimationFrame(step);
    }

    /* ── Toast Notification System ──────────────────────────── */

    /**
     * Display a toast notification.
     * @param {string} message - The message to display.
     * @param {string} [type='info'] - Type: 'success', 'error', 'warning', 'info'.
     * @param {number} [duration=4000] - Auto-dismiss delay in ms.
     */
    function showToast(message, type, duration) {
        if (typeof type === 'undefined') { type = 'info'; }
        if (typeof duration === 'undefined') { duration = 4000; }

        var container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            container.id = 'toastContainer';
            document.body.appendChild(container);
        }

        var iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        var colorMap = {
            success: 'var(--accent-green)',
            error: '#EF4444',
            warning: 'var(--accent-orange)',
            info: 'var(--accent-cyan)'
        };

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;

        var icon = document.createElement('span');
        icon.className = 'toast-icon';
        icon.innerHTML = '<i class="' + (iconMap[type] || iconMap.info) + '"></i>';
        icon.style.color = colorMap[type] || colorMap.info;

        var text = document.createElement('span');
        text.textContent = message;

        var closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.setAttribute('aria-label', 'Close notification');
        closeBtn.addEventListener('click', function () {
            dismissToast(toast);
        });

        toast.appendChild(icon);
        toast.appendChild(text);
        toast.appendChild(closeBtn);
        container.appendChild(toast);

        /* Auto-dismiss after duration */
        var autoTimer = setTimeout(function () {
            dismissToast(toast);
        }, duration);

        toast._autoTimer = autoTimer;
    }

    /**
     * Dismiss a toast with a fade-out transition.
     * @param {HTMLElement} toast - The toast element to remove.
     */
    function dismissToast(toast) {
        if (!toast || !toast.parentNode) return;
        if (toast._autoTimer) clearTimeout(toast._autoTimer);
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(80px)';
        setTimeout(function () {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    /* ── AJAX / Fetch Helper ────────────────────────────────── */

    /**
     * Wrapper around fetch with CSRF token and JSON support.
     * @param {string} url - The URL to request.
     * @param {object} [options={}] - Fetch options override.
     * @returns {Promise<Response>} The fetch response.
     */
    function intellihubFetch(url, options) {
        if (typeof options === 'undefined') { options = {}; }

        var csrfToken = getCookie('csrftoken');

        var defaultHeaders = {
            'X-CSRFToken': csrfToken || '',
            'X-Requested-With': 'XMLHttpRequest'
        };

        /* Only set Content-Type for non-FormData bodies */
        if (options.body && !(options.body instanceof FormData)) {
            defaultHeaders['Content-Type'] = 'application/json';
        }

        var mergedHeaders = Object.assign({}, defaultHeaders, options.headers || {});

        var fetchOptions = Object.assign({}, {
            method: 'GET',
            credentials: 'same-origin'
        }, options, {
            headers: mergedHeaders
        });

        /* Convert plain objects to JSON string */
        if (fetchOptions.body && typeof fetchOptions.body === 'object' && !(fetchOptions.body instanceof FormData)) {
            fetchOptions.body = JSON.stringify(fetchOptions.body);
        }

        return fetch(url, fetchOptions).then(function (response) {
            if (!response.ok) {
                return response.text().then(function (text) {
                    var errorMsg = 'Request failed with status ' + response.status;
                    try {
                        var json = JSON.parse(text);
                        if (json.error) errorMsg = json.error;
                        if (json.message) errorMsg = json.message;
                    } catch (e) {
                        /* Not JSON — keep default error message */
                    }
                    showToast(errorMsg, 'error');
                    throw new Error(errorMsg);
                });
            }
            return response;
        }).catch(function (err) {
            if (err.message !== 'Failed to fetch') {
                /* Already shown by .then handler above */
            } else {
                showToast('Network error. Please check your connection.', 'error');
            }
            throw err;
        });
    }

    /* ── Loading Overlay ────────────────────────────────────── */

    /**
     * Show the full-screen loading overlay.
     */
    function showLoading() {
        var overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }

    /**
     * Hide the full-screen loading overlay.
     */
    function hideLoading() {
        var overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    /* ── Form Validation Helper ─────────────────────────────── */

    /**
     * Highlight required fields that are empty in a form.
     * @param {HTMLFormElement} form - The form element to validate.
     * @returns {boolean} True if all required fields are filled.
     */
    function highlightInvalidFields(form) {
        if (!form) return false;
        var isValid = true;
        var requiredFields = form.querySelectorAll('[required]');

        requiredFields.forEach(function (field) {
            /* Reset previous state */
            field.style.borderColor = '';

            var value = field.value ? field.value.trim() : '';
            if (!value) {
                field.style.borderColor = '#EF4444';
                field.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.15)';
                isValid = false;
            }
        });

        if (!isValid) {
            showToast('Please fill in all required fields.', 'warning');
            /* Focus the first invalid field */
            var firstInvalid = form.querySelector('[required]');
            requiredFields.forEach(function (f) {
                if (!f.value.trim() && !firstInvalid._focused) {
                    f.focus();
                    firstInvalid._focused = true;
                }
            });
        }

        /* Clear red border on input/change */
        requiredFields.forEach(function (field) {
            field.addEventListener('input', function () {
                if (field.value.trim()) {
                    field.style.borderColor = '';
                    field.style.boxShadow = '';
                }
            }, { once: true });
        });

        return isValid;
    }

    /* ── Confirm Delete Modal ───────────────────────────────── */

    /**
     * Show a confirmation modal before deleting an item via POST.
     * @param {string} url - The URL to POST to for deletion.
     * @param {string} itemName - Human-readable name of the item.
     */
    function confirmDelete(url, itemName) {
        /* Remove any existing modals */
        var existing = document.querySelector('.confirm-modal-overlay');
        if (existing) existing.parentNode.removeChild(existing);

        var overlay = document.createElement('div');
        overlay.className = 'confirm-modal-overlay';

        var modal = document.createElement('div');
        modal.className = 'confirm-modal';
        modal.innerHTML =
            '<h3>Confirm Delete</h3>' +
            '<p>Are you sure you want to delete <strong>"' + escapeHtml(itemName) + '"</strong>? This action cannot be undone.</p>' +
            '<div class="confirm-modal-actions">' +
                '<button class="btn-glow-outline" id="confirmCancelBtn">Cancel</button>' +
                '<button class="btn-danger" id="confirmDeleteBtn">Delete</button>' +
            '</div>';

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        /* Cancel */
        document.getElementById('confirmCancelBtn').addEventListener('click', function () {
            overlay.parentNode.removeChild(overlay);
        });

        /* Close on overlay click */
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) {
                overlay.parentNode.removeChild(overlay);
            }
        });

        /* Confirm delete via POST */
        document.getElementById('confirmDeleteBtn').addEventListener('click', function () {
            var csrfToken = getCookie('csrftoken');
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = url;
            form.style.display = 'none';

            var csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrfToken || '';
            form.appendChild(csrfInput);

            document.body.appendChild(form);
            form.submit();
        });

        /* Escape key to close */
        function handleEsc(e) {
            if (e.key === 'Escape') {
                if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
                document.removeEventListener('keydown', handleEsc);
            }
        }
        document.addEventListener('keydown', handleEsc);
    }

    /**
     * Escape HTML entities to prevent XSS.
     * @param {string} text - Raw text.
     * @returns {string} Escaped HTML string.
     */
    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    /* ── Sidebar Toggle (Mobile) ────────────────────────────── */

    function initSidebar() {
        var menuBtn = document.getElementById('mobileMenuBtn');
        var sidebar = document.getElementById('sidebar');

        if (!menuBtn || !sidebar) return;

        menuBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            sidebar.classList.toggle('active');

            /* Create or toggle overlay */
            var overlay = document.querySelector('.sidebar-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'sidebar-overlay';
                document.body.appendChild(overlay);
                overlay.addEventListener('click', function () {
                    closeSidebar();
                });
            }
            overlay.classList.toggle('active');
        });

        /* Close sidebar on outside click (mobile) */
        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
                if (!sidebar.contains(e.target) && e.target !== menuBtn && !menuBtn.contains(e.target)) {
                    closeSidebar();
                }
            }
        });

        function closeSidebar() {
            sidebar.classList.remove('active');
            var overlay = document.querySelector('.sidebar-overlay');
            if (overlay) overlay.classList.remove('active');
        }
    }

    /* ── Drag-and-Drop File Upload ──────────────────────────── */

    function initDropzone() {
        var dropzones = document.querySelectorAll('.dropzone');
        if (!dropzones.length) return;

        dropzones.forEach(function (dropzone) {
            var fileInputId = dropzone.getAttribute('data-file-input');
            var fileInput = fileInputId ? document.getElementById(fileInputId) : dropzone.querySelector('input[type="file"]');
            var filenameDisplay = dropzone.querySelector('.dropzone-filename');

            /* Prevent default drag behaviors */
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function (eventName) {
                dropzone.addEventListener(eventName, function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                }, false);
            });

            /* Highlight on drag enter/over */
            ['dragenter', 'dragover'].forEach(function (eventName) {
                dropzone.addEventListener(eventName, function () {
                    dropzone.classList.add('dragover');
                }, false);
            });

            /* Remove highlight on drag leave/drop */
            ['dragleave', 'drop'].forEach(function (eventName) {
                dropzone.addEventListener(eventName, function () {
                    dropzone.classList.remove('dragover');
                }, false);
            });

            /* Handle drop */
            dropzone.addEventListener('drop', function (e) {
                var files = e.dataTransfer.files;
                if (files.length && fileInput) {
                    fileInput.files = files;
                    updateFilenameDisplay(files, filenameDisplay);
                    /* Trigger change event */
                    var changeEvent = new Event('change', { bubbles: true });
                    fileInput.dispatchEvent(changeEvent);
                }
            }, false);

            /* Click to open file dialog */
            dropzone.addEventListener('click', function () {
                if (fileInput) fileInput.click();
            });

            /* Update display when file selected via dialog */
            if (fileInput) {
                fileInput.addEventListener('change', function () {
                    updateFilenameDisplay(fileInput.files, filenameDisplay);
                });
            }
        });

        function updateFilenameDisplay(files, displayEl) {
            if (!displayEl) return;
            if (files.length === 1) {
                displayEl.textContent = files[0].name + ' (' + formatFileSize(files[0].size) + ')';
            } else if (files.length > 1) {
                displayEl.textContent = files.length + ' files selected';
            }
        }
    }

    /* ── Auto-Dismiss Django Messages ───────────────────────── */

    function initDjangoMessages() {
        var messagesContainer = document.querySelector('.django-messages');
        if (!messagesContainer) return;

        var messages = messagesContainer.querySelectorAll('[data-type]');
        messages.forEach(function (msg) {
            var tags = msg.getAttribute('data-type') || 'info';
            var text = msg.textContent.trim();

            /* Map Django message tags to toast types */
            var typeMap = {
                'success': 'success',
                'error': 'error',
                'danger': 'error',
                'warning': 'warning',
                'info': 'info',
                'debug': 'info'
            };

            var toastType = 'info';
            var tagsList = tags.split(' ');
            for (var i = 0; i < tagsList.length; i++) {
                var tag = tagsList[i].trim().toLowerCase();
                if (typeMap[tag]) {
                    toastType = typeMap[tag];
                    break;
                }
            }

            if (text) {
                showToast(text, toastType, 5000);
            }
        });

        /* Remove the hidden messages container */
        messagesContainer.parentNode.removeChild(messagesContainer);
    }

    /* ── Search Input Handler ───────────────────────────────── */

    function initSearchInput() {
        var searchInputs = document.querySelectorAll('.search-input');
        if (!searchInputs.length) return;

        searchInputs.forEach(function (input) {
            var debouncedSearch = debounce(function () {
                var query = input.value.trim();
                var targetUrl = input.getAttribute('data-search-url');
                var targetContainer = input.getAttribute('data-search-target');

                if (targetUrl && targetContainer) {
                    var separator = targetUrl.indexOf('?') !== -1 ? '&' : '?';
                    var url = targetUrl + separator + 'q=' + encodeURIComponent(query);

                    intellihubFetch(url).then(function (response) {
                        return response.text();
                    }).then(function (html) {
                        var container = document.querySelector(targetContainer);
                        if (container) {
                            container.innerHTML = html;
                        }
                    }).catch(function () {
                        /* Error already shown via intellihubFetch */
                    });
                }

                /* Dispatch custom event for manual handling */
                var event = new CustomEvent('intellihub:search', {
                    detail: { query: query },
                    bubbles: true
                });
                input.dispatchEvent(event);
            }, 300);

            input.addEventListener('keyup', debouncedSearch);
        });
    }

    /* ── Count-Up Observer ──────────────────────────────────── */

    function initCountUpObserver() {
        var elements = document.querySelectorAll('[data-count]');
        if (!elements.length) return;

        if ('IntersectionObserver' in window) {
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        var el = entry.target;
                        var target = parseFloat(el.getAttribute('data-count'));
                        var duration = parseInt(el.getAttribute('data-duration'), 10) || 2000;
                        if (!isNaN(target)) {
                            animateCountUp(el, target, duration);
                        }
                        observer.unobserve(el);
                    }
                });
            }, { threshold: 0.3 });

            elements.forEach(function (el) {
                observer.observe(el);
            });
        } else {
            /* Fallback: animate all immediately */
            elements.forEach(function (el) {
                var target = parseFloat(el.getAttribute('data-count'));
                var duration = parseInt(el.getAttribute('data-duration'), 10) || 2000;
                if (!isNaN(target)) {
                    animateCountUp(el, target, duration);
                }
            });
        }
    }

    /* ── Initialization ─────────────────────────────────────── */

    document.addEventListener('DOMContentLoaded', function () {
        initSidebar();
        initDropzone();
        initDjangoMessages();
        initSearchInput();
        initCountUpObserver();
    });

    /* ── Export to Global Scope ──────────────────────────────── */

    window.IntelliHub = {
        getCookie: getCookie,
        debounce: debounce,
        formatNumber: formatNumber,
        formatFileSize: formatFileSize,
        animateCountUp: animateCountUp,
        showToast: showToast,
        intellihubFetch: intellihubFetch,
        showLoading: showLoading,
        hideLoading: hideLoading,
        highlightInvalidFields: highlightInvalidFields,
        confirmDelete: confirmDelete,
        escapeHtml: escapeHtml
    };

    /* Also expose top-level convenience functions */
    window.showToast = showToast;
    window.showLoading = showLoading;
    window.hideLoading = hideLoading;
    window.confirmDelete = confirmDelete;
    window.intellihubFetch = intellihubFetch;
    window.formatNumber = formatNumber;
    window.formatFileSize = formatFileSize;
    window.debounce = debounce;
    window.getCookie = getCookie;
    window.animateCountUp = animateCountUp;
    window.highlightInvalidFields = highlightInvalidFields;

})();
