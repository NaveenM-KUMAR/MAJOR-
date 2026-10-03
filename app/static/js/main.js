/**
 * Community Parking System — Core JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });

    // Initialize Geolocation Auto-Detection if element exists
    const geoBtn = document.getElementById('detectLocationBtn');
    if (geoBtn) {
        geoBtn.addEventListener('click', () => {
            if (navigator.geolocation) {
                geoBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Locating...';
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        const lat = pos.coords.latitude;
                        const lng = pos.coords.longitude;
                        
                        const latInput = document.getElementById('latInput');
                        const lngInput = document.getElementById('lngInput');
                        if (latInput && lngInput) {
                            latInput.value = lat;
                            lngInput.value = lng;
                        }
                        
                        // If on search or emergency page, reload with coordinates
                        const urlParams = new URLSearchParams(window.location.search);
                        urlParams.set('lat', lat);
                        urlParams.set('lng', lng);
                        window.location.search = urlParams.toString();
                    },
                    (err) => {
                        showToast('Could not retrieve your location. Please ensure location permissions are enabled.', 'warning');
                        geoBtn.innerHTML = '<i class="bi bi-geo-alt-fill me-1"></i> Use My Location';
                    }
                );
            } else {
                showToast('Geolocation is not supported by your browser.', 'danger');
            }
        });
    }

    // Modern Bootstrap Toast Notification Helper
    function showToast(message, type = 'warning') {
        let toastContainer = document.getElementById('cps-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'cps-toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1100';
            document.body.appendChild(toastContainer);
        }
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-bg-${type} border-0 shadow`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body small fw-semibold">
                    <i class="bi bi-info-circle me-1"></i> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        toastContainer.appendChild(toastEl);
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toastEl, { delay: 5000 });
            bsToast.show();
            toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
        }
    }

    // Dynamic Live Slot Availability Check on Booking Form
    const bookingDateInput = document.getElementById('booking_date');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    const spaceIdInput = document.getElementById('parking_space_id');
    const availNotice = document.getElementById('liveAvailabilityNotice');
    const priceDisplay = document.getElementById('dynamicPriceDisplay');
    const pricePerHourVal = parseFloat(document.getElementById('pricePerHourVal')?.value || 0);

    function checkLiveAvailability() {
        if (!bookingDateInput || !startTimeInput || !endTimeInput || !spaceIdInput || !availNotice) return;
        
        const dateVal = bookingDateInput.value;
        const startVal = startTimeInput.value;
        const endVal = endTimeInput.value;
        const spaceId = spaceIdInput.value;

        if (dateVal && startVal && endVal) {
            availNotice.innerHTML = '<span class="spinner-border spinner-border-sm text-primary"></span> Checking slot availability...';
            availNotice.className = 'alert alert-info py-2 small';

            fetch(`/api/parking/${spaceId}/availability?date=${dateVal}&start_time=${startVal}&end_time=${endVal}`)
                .then(res => res.json())
                .then(data => {
                    if (data.available) {
                        availNotice.innerHTML = `<i class="bi bi-check-circle-fill me-1"></i> ${data.message}`;
                        availNotice.className = 'alert alert-success py-2 small';
                    } else {
                        availNotice.innerHTML = `<i class="bi bi-exclamation-octagon-fill me-1"></i> ${data.message}`;
                        availNotice.className = 'alert alert-danger py-2 small';
                    }

                    // Calculate estimated price
                    if (priceDisplay && startVal < endVal) {
                        const sH = parseInt(startVal.split(':')[0]) + parseInt(startVal.split(':')[1])/60;
                        const eH = parseInt(endVal.split(':')[0]) + parseInt(endVal.split(':')[1])/60;
                        const dur = Math.max(0.5, eH - sH);
                        const estPrice = (dur * pricePerHourVal).toFixed(2);
                        priceDisplay.innerText = `₹${estPrice} (${dur.toFixed(1)} hrs)`;
                    }
                })
                .catch(err => {
                    availNotice.innerHTML = 'Could not verify availability live.';
                    availNotice.className = 'alert alert-secondary py-2 small';
                });
        }
    }

    if (bookingDateInput && startTimeInput && endTimeInput) {
        bookingDateInput.addEventListener('change', checkLiveAvailability);
        startTimeInput.addEventListener('change', checkLiveAvailability);
        endTimeInput.addEventListener('change', checkLiveAvailability);
    }
});
