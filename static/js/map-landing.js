// Map Landing - World Map with Stable Dots + Hover Balloons

// Mapbox Access Token
mapboxgl.accessToken = 'pk.eyJ1IjoibmV4dXNtZW1vaXIiLCJhIjoiY21rb2sycXN4MDhnMTNjc2FxYWtxaXY1byJ9.PEZQ7jJ02OJZ0ndCVEcc8g';

// Sample capsule data (world locations)
const sampleCapsules = [
    { id: 1, lat: 41.0082, lng: 28.9784, title: "Ela'nın İlk Adımları", date: "14 Mayıs 2028", city: "Istanbul", status: "locked" },
    { id: 2, lat: 39.9334, lng: 32.8597, title: "Ankara Anıları", date: "25 Aralık 2026", city: "Ankara", status: "locked" },
    { id: 3, lat: 38.4237, lng: 27.1428, title: "Ege'nin Mavi Anıları", date: "15 Haziran 2027", city: "Izmir", status: "locked" },
    { id: 4, lat: 48.8566, lng: 2.3522, title: "Paris Love Story", date: "14 Şubat 2027", city: "Paris", status: "locked" },
    { id: 5, lat: 40.7128, lng: -74.0060, title: "Times Square Memories", date: "31 Aralık 2026", city: "New York", status: "locked" },
    { id: 6, lat: 35.6762, lng: 139.6503, title: "桜の思い出", date: "3 Nisan 2027", city: "Tokyo", status: "locked" },
];

// Initialize map (world view)
const map = new mapboxgl.Map({
    container: 'mainMap',
    style: {
        version: 8,
        sources: {
            'carto-light': {
                type: 'raster',
                tiles: ['https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],
                tileSize: 256
            }
        },
        layers: [
            {
                id: 'background',
                type: 'background',
                paint: {
                    'background-color': '#f5e6ff'
                }
            },
            {
                id: 'carto-tiles',
                type: 'raster',
                source: 'carto-light',
                paint: {
                    'raster-opacity': 0.9
                }
            }
        ]
    },
    center: [20, 30],
    zoom: 2.5,
    minZoom: 2,
    maxZoom: 18
});

// Add navigation controls
map.addControl(new mapboxgl.NavigationControl());

// Create stable dot marker
function createDotMarker() {
    const el = document.createElement('div');
    el.className = 'capsule-dot-stable';
    el.innerHTML = `
        <div class="dot-inner-stable"></div>
        <div class="dot-ring-stable"></div>
    `;
    return el;
}

// Create hover balloon popup
function createHoverPopup(capsule) {
    const icon = capsule.status === 'locked' ? '🔒' : '🎉';
    
    return `
        <div class="hover-balloon">
            <div class="hover-title">${capsule.title}</div>
            <div class="hover-city">📍 ${capsule.city}</div>
            <div class="hover-date">${capsule.date}</div>
            <div class="hover-status">${icon} ${capsule.status === 'locked' ? 'Kilitli' : 'Açık'}</div>
        </div>
    `;
}

// Add markers when map loads
map.on('load', function() {
    sampleCapsules.forEach(capsule => {
        const el = createDotMarker();
        
        // Create hover popup
        const popup = new mapboxgl.Popup({
            offset: 25,
            closeButton: false,
            closeOnClick: false,
            className: 'hover-popup'
        }).setHTML(createHoverPopup(capsule));
        
        // Add marker
        const marker = new mapboxgl.Marker({
            element: el,
            anchor: 'center'
        })
        .setLngLat([capsule.lng, capsule.lat])
        .addTo(map);
        
        // Hover to show popup
        el.addEventListener('mouseenter', () => {
            marker.setPopup(popup);
            marker.togglePopup();
        });
        
        el.addEventListener('mouseleave', () => {
            marker.togglePopup();
        });
        
        // Click to open detail
        el.addEventListener('click', () => {
            alert(`${capsule.title}\n📍 ${capsule.city}\n📅 ${capsule.date}\n${capsule.status === 'locked' ? '🔒 Kilitli' : '🎉 Açık'}`);
        });
    });
});

// Add CSS for stable dots and hover balloons
const style = document.createElement('style');
style.textContent = `
    .capsule-dot-stable {
        width: 20px;
        height: 20px;
        cursor: pointer;
        position: relative;
        transition: transform 0.2s;
    }
    
    .capsule-dot-stable:hover {
        transform: scale(1.3);
        z-index: 10;
    }
    
    .dot-inner-stable {
        width: 12px;
        height: 12px;
        background: linear-gradient(135deg, #ff6b9d, #ffa94d);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        box-shadow: 0 0 15px rgba(255, 107, 157, 0.8);
        animation: pulse-stable 2s ease-in-out infinite;
    }
    
    @keyframes pulse-stable {
        0%, 100% {
            box-shadow: 0 0 15px rgba(255, 107, 157, 0.8);
        }
        50% {
            box-shadow: 0 0 25px rgba(255, 107, 157, 1);
        }
    }
    
    .dot-ring-stable {
        width: 20px;
        height: 20px;
        border: 2px solid rgba(255, 107, 157, 0.4);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        animation: ring-stable 2s ease-in-out infinite;
    }
    
    @keyframes ring-stable {
        0%, 100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
        }
        50% {
            transform: translate(-50%, -50%) scale(1.4);
            opacity: 0.4;
        }
    }
    
    /* Hover Balloon */
    .hover-balloon {
        padding: 8px 12px;
        min-width: 180px;
    }
    
    .hover-title {
        font-size: 15px;
        font-weight: 700;
        color: #0f0f23;
        margin-bottom: 6px;
    }
    
    .hover-city {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 4px;
    }
    
    .hover-date {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 8px;
    }
    
    .hover-status {
        font-size: 12px;
        font-weight: 600;
        color: white;
        background: linear-gradient(135deg, #ff6b9d, #ffa94d);
        padding: 5px 10px;
        border-radius: 8px;
        display: inline-block;
    }
    
    .hover-popup .mapboxgl-popup-content {
        background: white;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
        border: 2px solid rgba(255, 107, 157, 0.4);
    }
    
    .hover-popup .mapboxgl-popup-tip {
        border-top-color: white;
    }
`;
document.head.appendChild(style);

// Animate stats on page load
function animateStats() {
    const totalEl = document.getElementById('totalCapsules');
    const citiesEl = document.getElementById('countries');
    
    if (totalEl) {
        let count = 0;
        const target = 89;
        const interval = setInterval(() => {
            count += 2;
            if (count >= target) {
                count = target;
                clearInterval(interval);
            }
            totalEl.textContent = count;
        }, 25);
    }
    
    if (citiesEl) {
        const label = citiesEl.nextElementSibling;
        if (label && label.classList.contains('stat-label-compact')) {
            label.textContent = 'Şehir';
        }
        
        let count = 0;
        const target = 47;
        const interval = setInterval(() => {
            count += 1;
            if (count >= target) {
                count = target;
                clearInterval(interval);
            }
            citiesEl.textContent = count;
        }, 50);
    }
}

document.addEventListener('DOMContentLoaded', animateStats);

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

console.log('World map with stable dots and hover balloons initialized!');

const sampleCapsules = [
    { id: 1, lat: 41.0082, lng: 28.9784, title: "Ela'nın İlk Adımları", date: "14 Mayıs 2028", city: "Istanbul", status: "locked" },
    { id: 2, lat: 39.9334, lng: 32.8597, title: "Ankara Anıları", date: "25 Aralık 2026", city: "Ankara", status: "locked" },
    { id: 3, lat: 38.4237, lng: 27.1428, title: "Ege'nin Mavi Anıları", date: "15 Haziran 2027", city: "Izmir", status: "locked" },
    { id: 4, lat: 36.8969, lng: 30.7133, title: "Akdeniz Rüyası", date: "1 Ağustos 2027", city: "Antalya", status: "locked" },
    { id: 5, lat: 37.0000, lng: 35.3213, title: "Adana Güneşi", date: "10 Mart 2028", city: "Adana", status: "locked" },
    { id: 6, lat: 40.1826, lng: 29.0670, title: "Bursa Yeşili", date: "5 Mayıs 2027", city: "Bursa", status: "locked" },
    { id: 7, lat: 37.8667, lng: 32.4833, title: "Konya'dan Mesajlar", date: "20 Haziran 2028", city: "Konya", status: "locked" },
    { id: 8, lat: 36.2000, lng: 36.1600, title: "Hatay Lezzeti", date: "15 Ekim 2027", city: "Hatay", status: "locked" }
];

// Initialize map (Turkey focused)
const map = new mapboxgl.Map({
    container: 'mainMap',
    style: {
        version: 8,
        sources: {
            'carto-light': {
                type: 'raster',
                tiles: ['https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],
                tileSize: 256
            }
        },
        layers: [
            {
                id: 'background',
                type: 'background',
                paint: {
                    'background-color': '#f5e6ff'
                }
            },
            {
                id: 'carto-tiles',
                type: 'raster',
                source: 'carto-light',
                paint: {
                    'raster-opacity': 0.9
                }
            }
        ]
    },
    center: [35.2433, 38.9637], // Turkey center
    zoom: 6,
    minZoom: 5.5,
    maxZoom: 18,
    maxBounds: [[25, 35], [45, 43]] // Turkey bounds
});

// Add navigation controls
map.addControl(new mapboxgl.NavigationControl());

// Create dot marker (no balloon, just a dot)
function createDotMarker() {
    const el = document.createElement('div');
    el.className = 'capsule-dot';
    el.innerHTML = `
        <div class="dot-inner"></div>
        <div class="dot-ring"></div>
    `;
    return el;
}

// Create popup content
function createPopupContent(capsule) {
    const icon = capsule.status === 'locked' ? '🔒' : '🎉';
    
    return `
        <div class="capsule-popup">
            <div class="popup-title">${capsule.title}</div>
            <div class="popup-city">📍 ${capsule.city}</div>
            <div class="popup-date">${capsule.date}</div>
            <div class="popup-status">${icon} ${capsule.status === 'locked' ? 'Kilitli' : 'Açık'}</div>
        </div>
    `;
}

// Add markers when map loads
map.on('load', function() {
    sampleCapsules.forEach(capsule => {
        const el = createDotMarker();
        
        // Create popup (opens on click, not hover)
        const popup = new mapboxgl.Popup({
            offset: 25,
            closeButton: true,
            closeOnClick: false,
            maxWidth: '300px'
        }).setHTML(createPopupContent(capsule));
        
        // Add marker with popup
        const marker = new mapboxgl.Marker({
            element: el,
            anchor: 'center'
        })
        .setLngLat([capsule.lng, capsule.lat])
        .setPopup(popup)
        .addTo(map);
        
        // Click to toggle popup
        el.addEventListener('click', () => {
            marker.togglePopup();
        });
    });
});

// Add CSS for dot markers and popups
const style = document.createElement('style');
style.textContent = `
    .capsule-dot {
        width: 20px;
        height: 20px;
        cursor: pointer;
        position: relative;
        transition: transform 0.2s;
    }
    
    .capsule-dot:hover {
        transform: scale(1.4);
    }
    
    .dot-inner {
        width: 12px;
        height: 12px;
        background: linear-gradient(135deg, #ff6b9d, #ffa94d);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        box-shadow: 0 0 15px rgba(255, 107, 157, 0.7);
        animation: pulse-dot 2s ease-in-out infinite;
    }
    
    @keyframes pulse-dot {
        0%, 100% {
            box-shadow: 0 0 15px rgba(255, 107, 157, 0.7);
        }
        50% {
            box-shadow: 0 0 25px rgba(255, 107, 157, 1);
        }
    }
    
    .dot-ring {
        width: 20px;
        height: 20px;
        border: 2px solid rgba(255, 107, 157, 0.4);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        animation: ring-expand 2s ease-in-out infinite;
    }
    
    @keyframes ring-expand {
        0%, 100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
        }
        50% {
            transform: translate(-50%, -50%) scale(1.5);
            opacity: 0.3;
        }
    }
    
    /* Popup Styles */
    .capsule-popup {
        padding: 0.25rem;
        min-width: 180px;
    }
    
    .popup-title {
        font-size: 15px;
        font-weight: 700;
        color: #0f0f23;
        margin-bottom: 6px;
        line-height: 1.3;
    }
    
    .popup-city {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 4px;
    }
    
    .popup-date {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 8px;
    }
    
    .popup-status {
        font-size: 12px;
        font-weight: 600;
        color: white;
        background: linear-gradient(135deg, #ff6b9d, #ffa94d);
        padding: 6px 12px;
        border-radius: 8px;
        display: inline-block;
    }
    
    .mapboxgl-popup-content {
        background: white;
        padding: 14px;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
        border: 2px solid rgba(255, 107, 157, 0.4);
    }
    
    .mapboxgl-popup-close-button {
        font-size: 20px;
        color: #94a3b8;
        padding: 4px 8px;
        font-weight: 300;
    }
    
    .mapboxgl-popup-close-button:hover {
        color: #ff6b9d;
        background: transparent;
    }
    
    .mapboxgl-popup-tip {
        border-top-color: white;
        border-width: 10px;
    }
`;
document.head.appendChild(style);

// Animate stats on page load
function animateStats() {
    const totalEl = document.getElementById('totalCapsules');
    const citiesEl = document.getElementById('countries');
    
    if (totalEl) {
        let count = 0;
        const target = 89;
        const interval = setInterval(() => {
            count += 2;
            if (count >= target) {
                count = target;
                clearInterval(interval);
            }
            totalEl.textContent = count;
        }, 25);
    }
    
    if (citiesEl) {
        // Change label to "İl"
        const label = citiesEl.nextElementSibling;
        if (label && label.classList.contains('stat-label-compact')) {
            label.textContent = 'İl';
        }
        
        let count = 0;
        const target = 47;
        const interval = setInterval(() => {
            count += 1;
            if (count >= target) {
                count = target;
                clearInterval(interval);
            }
            citiesEl.textContent = count;
        }, 50);
    }
}

document.addEventListener('DOMContentLoaded', animateStats);

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

console.log('Turkey-focused map initialized with dot markers!');
