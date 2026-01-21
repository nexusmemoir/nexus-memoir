// Globe Hero - Interactive 3D World with Capsules

// Sample capsule data (will come from database later)
const sampleCapsules = [
    { lat: 41.0082, lng: 28.9784, title: "Ela'nın İlk Adımları", city: "Istanbul", size: 0.8, color: '#f59e0b' },
    { lat: 48.8566, lng: 2.3522, title: "Notre Amour Éternel", city: "Paris", size: 0.6, color: '#ec4899' },
    { lat: 35.6762, lng: 139.6503, title: "桜の思い出", city: "Tokyo", size: 0.7, color: '#10b981' },
    { lat: 40.7128, lng: -74.0060, title: "Times Square Memories", city: "New York", size: 0.5, color: '#6366f1' },
    { lat: 51.5074, lng: -0.1278, title: "London Calling", city: "London", size: 0.4, color: '#8b5cf6' },
    { lat: -33.8688, lng: 151.2093, title: "Down Under Dreams", city: "Sydney", size: 0.6, color: '#ec4899' },
    { lat: 55.7558, lng: 37.6173, title: "Red Square Romance", city: "Moscow", size: 0.5, color: '#f59e0b' },
    { lat: 25.2048, lng: 55.2708, title: "Desert Miracle", city: "Dubai", size: 0.7, color: '#6366f1' },
];

// Initialize globe
const globe = Globe()
    (document.getElementById('globeViz'))
    .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
    .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
    .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
    .pointsData(sampleCapsules)
    .pointLat('lat')
    .pointLng('lng')
    .pointColor('color')
    .pointAltitude(0.01)
    .pointRadius('size')
    .pointLabel(d => `
        <div style="background: rgba(15, 15, 35, 0.95); padding: 12px 16px; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.3); backdrop-filter: blur(10px);">
            <div style="font-size: 14px; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">${d.title}</div>
            <div style="font-size: 12px; color: #94a3b8;">📍 ${d.city}</div>
        </div>
    `)
    .onPointClick(d => {
        console.log('Capsule clicked:', d);
        // Will open capsule detail modal
    });

// Auto-rotate
globe.controls().autoRotate = true;
globe.controls().autoRotateSpeed = 0.5;

// Responsive sizing
function resizeGlobe() {
    const container = document.getElementById('globeViz');
    if (container) {
        const width = container.offsetWidth;
        const height = container.offsetHeight;
        globe.width(width).height(height);
    }
}

window.addEventListener('resize', resizeGlobe);
resizeGlobe();

// Initial camera position
globe.pointOfView({ lat: 41, lng: 29, altitude: 2.5 }, 1000);

// Add pulsing animation to points
setInterval(() => {
    const points = globe.pointsData();
    points.forEach(p => {
        p.size = 0.4 + Math.random() * 0.4;
    });
    globe.pointsData(points);
}, 2000);

// Update stats in real-time
function updateStats() {
    // Animate total capsules
    const totalEl = document.getElementById('totalCapsules');
    if (totalEl) {
        let current = 0;
        const target = 127;
        const duration = 2000;
        const increment = target / (duration / 16);
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            totalEl.textContent = Math.floor(current);
        }, 16);
    }
    
    // Countries count
    const countriesEl = document.getElementById('countries');
    if (countriesEl) {
        let current = 0;
        const target = 23;
        const timer = setInterval(() => {
            current++;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            countriesEl.textContent = current;
        }, 100);
    }
}

// Run stats animation on page load
document.addEventListener('DOMContentLoaded', updateStats);

// Next opening countdown
function updateNextOpening() {
    const el = document.getElementById('nextOpening');
    if (!el) return;
    
    // Sample: 3 days, 14 hours from now
    const targetDate = new Date(Date.now() + (3 * 24 * 60 * 60 * 1000) + (14 * 60 * 60 * 1000));
    
    function update() {
        const now = new Date();
        const diff = targetDate - now;
        
        if (diff <= 0) {
            el.textContent = 'Şimdi!';
            return;
        }
        
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        
        el.textContent = `${days}g ${hours}s`;
    }
    
    update();
    setInterval(update, 60000); // Update every minute
}

updateNextOpening();

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});
