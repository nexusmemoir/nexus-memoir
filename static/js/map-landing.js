// Map Landing - 2D Interactive Map with Balloon Capsules

// Mapbox Access Token
mapboxgl.accessToken = 'pk.eyJ1IjoibmV4dXNtZW1vaXIiLCJhIjoiY21rb2sycXN4MDhnMTNjc2FxYWtxaXY1byJ9.PEZQ7jJ02OJZ0ndCVEcc8g';

// Sample capsule data (will come from API later)
const sampleCapsules = [
    { id: 1, lat: 41.0082, lng: 28.9784, title: "Ela'nın İlk Adımları", date: "14 Mayıs 2028", zone: "premium", status: "locked" },
    { id: 2, lat: 48.8566, lng: 2.3522, title: "Notre Amour Éternel", date: "25 Aralık 2026", zone: "premium", status: "locked" },
    { id: 3, lat: 35.6762, lng: 139.6503, title: "桜の思い出", date: "3 Nisan 2027", zone: "premium", status: "locked" },
    { id: 4, lat: 40.7128, lng: -74.0060, title: "Times Square Memories", date: "31 Aralık 2026", zone: "premium", status: "locked" },
    { id: 5, lat: 38.4237, lng: 27.1428, title: "Ege'nin Mavi Anıları", date: "15 Haziran 2027", zone: "popular", status: "locked" },
    { id: 6, lat: 52.5200, lng: 13.4050, title: "Berlin Love Story", date: "9 Kasım 2027", zone: "popular", status: "locked" },
    { id: 7, lat: 37.8667, lng: 32.4833, title: "Konya Anıları", date: "10 Mart 2028", zone: "standard", status: "locked" },
    { id: 8, lat: 51.5074, lng: -0.1278, title: "London Calling", date: "1 Ocak 2027", zone: "premium", status: "locked" },
];

// Zone colors
const zoneColors = {
    premium: '#ff6b9d',
    popular: '#ffa94d',
    standard: '#ffd93d',
    basic: '#95e1d3'
};

// Initialize map
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
                    'raster-opacity': 0.85
                }
            }
        ]
    },
    center: [20, 30],
    zoom: 2,
    minZoom: 2,
    maxZoom: 18
});

// Add navigation controls
map.addControl(new mapboxgl.NavigationControl());

// Create balloon marker HTML
function createBalloonHTML(capsule) {
    const color = zoneColors[capsule.zone];
    const icon = capsule.status === 'locked' ? '🔒' : '🎉';
    
    return `
        <div class="balloon-marker" style="border-color: ${color};">
            <div class="balloon-content">
                <div class="balloon-title">${capsule.title}</div>
                <div class="balloon-date">${capsule.date}</div>
                <div class="balloon-status">${icon} ${capsule.status === 'locked' ? 'Kilitli' : 'Açık'}</div>
            </div>
            <div class="balloon-pointer" style="border-top-color: ${color};"></div>
            <div class="balloon-pin" style="background: ${color};"></div>
        </div>
    `;
}

// Add markers when map loads
map.on('load', function() {
    sampleCapsules.forEach(capsule => {
        const el = document.createElement('div');
        el.className = 'custom-marker-container';
        el.innerHTML = createBalloonHTML(capsule);
        
        // Add hover effect
        el.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1) translateY(-5px)';
        });
        
        el.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1) translateY(0)';
        });
        
        // Click to show detail
        el.addEventListener('click', function() {
            alert(`${capsule.title}\nAçılış: ${capsule.date}\nDurum: ${capsule.status === 'locked' ? 'Kilitli' : 'Açık'}`);
        });
        
        new mapboxgl.Marker({
            element: el,
            anchor: 'bottom'
        })
        .setLngLat([capsule.lng, capsule.lat])
        .addTo(map);
    });
    
    // Add gentle rotation animation
    let rotation = 0;
    function rotateCamera() {
        map.rotateTo(rotation, { duration: 200000 });
        rotation = (rotation + 360) % 360;
        setTimeout(rotateCamera, 200000);
    }
    // rotateCamera(); // Uncomment for slow rotation
});

// Add CSS for balloon markers
const style = document.createElement('style');
style.textContent = `
    .custom-marker-container {
        cursor: pointer;
        transition: transform 0.3s ease;
    }
    
    .balloon-marker {
        position: relative;
        background: rgba(255, 255, 255, 0.98);
        padding: 12px 16px;
        border-radius: 16px;
        border: 3px solid;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        min-width: 180px;
        backdrop-filter: blur(10px);
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
    }
    
    .balloon-content {
        position: relative;
        z-index: 2;
    }
    
    .balloon-title {
        font-size: 14px;
        font-weight: 700;
        color: #0f0f23;
        margin-bottom: 4px;
        line-height: 1.3;
    }
    
    .balloon-date {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 6px;
    }
    
    .balloon-status {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        background: rgba(255, 255, 255, 0.8);
        padding: 4px 8px;
        border-radius: 8px;
        display: inline-block;
    }
    
    .balloon-pointer {
        position: absolute;
        bottom: -12px;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 12px solid transparent;
        border-right: 12px solid transparent;
        border-top: 12px solid;
        z-index: 1;
    }
    
    .balloon-pin {
        position: absolute;
        bottom: -32px;
        left: 50%;
        transform: translateX(-50%);
        width: 12px;
        height: 20px;
        border-radius: 50% 50% 50% 0;
        transform: translateX(-50%) rotate(-45deg);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .balloon-pin::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(45deg);
        width: 6px;
        height: 6px;
        background: white;
        border-radius: 50%;
    }
`;
document.head.appendChild(style);

// Animate stats on page load
function animateStats() {
    const totalEl = document.getElementById('totalCapsules');
    const countriesEl = document.getElementById('countries');
    
    if (totalEl) {
        let count = 0;
        const target = 156;
        const interval = setInterval(() => {
            count += 3;
            if (count >= target) {
                count = target;
                clearInterval(interval);
            }
            totalEl.textContent = count;
        }, 20);
    }
    
    if (countriesEl) {
        let count = 0;
        const target = 34;
        const interval = setInterval(() => {
            count += 1;
            if (count >= target) {
                count = target;
                clearInterval(interval);
            }
            countriesEl.textContent = count;
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

console.log('Map Landing initialized - 2D interactive map with balloon capsules!');
