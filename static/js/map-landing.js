// Map Landing - Stable Dots with NO jumping!

mapboxgl.accessToken = 'pk.eyJ1IjoibmV4dXNtZW1vaXIiLCJhIjoiY21rb2sycXN4MDhnMTNjc2FxYWtxaXY1byJ9.PEZQ7jJ02OJZ0ndCVEcc8g';

const sampleCapsules = [
    { id: 1, lat: 41.0082, lng: 28.9784, title: "Ela'nın İlk Adımları", date: "14 Mayıs 2028", city: "Istanbul", status: "locked" },
    { id: 2, lat: 39.9334, lng: 32.8597, title: "Ankara Anıları", date: "25 Aralık 2026", city: "Ankara", status: "locked" },
    { id: 3, lat: 38.4237, lng: 27.1428, title: "Ege'nin Mavi Anıları", date: "15 Haziran 2027", city: "Izmir", status: "locked" },
    { id: 4, lat: 48.8566, lng: 2.3522, title: "Paris Love Story", date: "14 Şubat 2027", city: "Paris", status: "locked" },
    { id: 5, lat: 40.7128, lng: -74.0060, title: "Times Square Memories", date: "31 Aralık 2026", city: "New York", status: "locked" },
    { id: 6, lat: 35.6762, lng: 139.6503, title: "桜の思い出", date: "3 Nisan 2027", city: "Tokyo", status: "locked" },
];

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
                paint: { 'background-color': '#f5e6ff' }
            },
            {
                id: 'carto-tiles',
                type: 'raster',
                source: 'carto-light',
                paint: { 'raster-opacity': 0.9 }
            }
        ]
    },
    center: [20, 30],
    zoom: 2.5,
    minZoom: 2,
    maxZoom: 18
});

map.addControl(new mapboxgl.NavigationControl());

function createPopupContent(capsule) {
    const icon = capsule.status === 'locked' ? '🔒' : '🎉';
    return `
        <div style="padding: 8px 12px; min-width: 180px;">
            <div style="font-size: 15px; font-weight: 700; color: #0f0f23; margin-bottom: 6px;">${capsule.title}</div>
            <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">📍 ${capsule.city}</div>
            <div style="font-size: 13px; color: #64748b; margin-bottom: 8px;">${capsule.date}</div>
            <div style="font-size: 12px; font-weight: 600; color: white; background: linear-gradient(135deg, #ff6b9d, #ffa94d); padding: 5px 10px; border-radius: 8px; display: inline-block;">${icon} ${capsule.status === 'locked' ? 'Kilitli' : 'Açık'}</div>
        </div>
    `;
}

map.on('load', function() {
    sampleCapsules.forEach(capsule => {
        // Create stable dot element
        const el = document.createElement('div');
        el.className = 'stable-dot-marker';
        el.innerHTML = `
            <div class="dot-core"></div>
            <div class="dot-ring"></div>
        `;
        
        // Create popup
        const popup = new mapboxgl.Popup({
            offset: 25,
            closeButton: true,
            closeOnClick: true,
            maxWidth: '300px'
        }).setHTML(createPopupContent(capsule));
        
        // Add marker
        const marker = new mapboxgl.Marker({
            element: el,
            anchor: 'center'
        })
        .setLngLat([capsule.lng, capsule.lat])
        .addTo(map);
        
        // Click to toggle popup
        el.addEventListener('click', () => {
            marker.setPopup(popup);
            marker.togglePopup();
        });
    });
});

// Add CSS
const style = document.createElement('style');
style.textContent = `
    .stable-dot-marker {
        width: 20px;
        height: 20px;
        cursor: pointer;
        position: relative;
        transition: transform 0.2s;
    }
    
    .stable-dot-marker:hover {
        transform: scale(1.3);
        z-index: 10;
    }
    
    .dot-core {
        width: 12px;
        height: 12px;
        background: linear-gradient(135deg, #ff6b9d, #ffa94d);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        box-shadow: 0 0 15px rgba(255, 107, 157, 0.8);
        animation: pulse-core 2s ease-in-out infinite;
    }
    
    @keyframes pulse-core {
        0%, 100% { box-shadow: 0 0 15px rgba(255, 107, 157, 0.8); }
        50% { box-shadow: 0 0 25px rgba(255, 107, 157, 1); }
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
        animation: ring-pulse 2s ease-in-out infinite;
        pointer-events: none;
    }
    
    @keyframes ring-pulse {
        0%, 100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
        }
        50% {
            transform: translate(-50%, -50%) scale(1.4);
            opacity: 0.4;
        }
    }
    
    .mapboxgl-popup-content {
        background: white;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
        border: 2px solid rgba(255, 107, 157, 0.4);
    }
    
    .mapboxgl-popup-close-button {
        font-size: 20px;
        color: #94a3b8;
        padding: 4px 8px;
    }
    
    .mapboxgl-popup-close-button:hover {
        color: #ff6b9d;
        background: transparent;
    }
`;
document.head.appendChild(style);

// Stats animation
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

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

console.log('Stable dots - NO jumping!');
