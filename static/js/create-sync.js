// Create Page - Turkey Focused + Shovel Animation

// Mapbox token
mapboxgl.accessToken = 'pk.eyJ1IjoibmV4dXNtZW1vaXIiLCJhIjoiY21rb2sycXN4MDhnMTNjc2FxYWtxaXY1byJ9.PEZQ7jJ02OJZ0ndCVEcc8g';

// Single price for all Turkey
const PRICE = 499;

let selectedLat = null;
let selectedLng = null;
let selectedLocationName = '';
let userMarker = null;

// Initialize map (Turkey focused, same as landing)
const map = new mapboxgl.Map({
    container: 'createMap',
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

// Add controls
map.addControl(new mapboxgl.NavigationControl());

// Update info display
function updateLocationInfo() {
    document.getElementById('currentZoneName').textContent = 'Türkiye';
    document.getElementById('currentZonePrice').textContent = `₺${PRICE}`;
}

updateLocationInfo();

// Create dot marker for user selection
function createUserDotMarker() {
    const el = document.createElement('div');
    el.className = 'user-dot-marker';
    el.innerHTML = `
        <div class="user-dot-inner"></div>
        <div class="user-dot-ring"></div>
    `;
    return el;
}

// Shovel + dirt animation (3 seconds)
function playShovelAnimation() {
    const overlay = document.getElementById('digAnimation');
    overlay.style.display = 'flex';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 3000);
}

// Map click handler
map.on('click', function(e) {
    selectedLat = e.latlng.lat;
    selectedLng = e.latlng.lng;
    
    // Play shovel animation
    playShovelAnimation();
    
    // Remove existing marker
    if (userMarker) {
        userMarker.remove();
    }
    
    // Wait for animation
    setTimeout(() => {
        // Add dot marker
        const el = createUserDotMarker();
        
        userMarker = new mapboxgl.Marker({
            element: el,
            anchor: 'center'
        })
        .setLngLat([selectedLng, selectedLat])
        .addTo(map);
        
        // Reverse geocode
        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${selectedLat}&lon=${selectedLng}`)
            .then(res => res.json())
            .then(data => {
                const city = data.address.city || data.address.town || data.address.village || data.address.province || data.address.state;
                const province = data.address.province || data.address.state;
                selectedLocationName = city ? `${city}, ${province || 'Türkiye'}` : (province || 'Türkiye');
                
                document.getElementById('locationName').textContent = selectedLocationName;
                document.getElementById('locationCoords').textContent = 
                    `Lat: ${selectedLat.toFixed(6)}, Lng: ${selectedLng.toFixed(6)}`;
                document.getElementById('selectedLocation').style.display = 'block';
                document.getElementById('continueBtn').disabled = false;
            })
            .catch(err => {
                console.error('Geocoding error:', err);
                selectedLocationName = 'Seçilen Lokasyon';
                document.getElementById('locationName').textContent = selectedLocationName;
                document.getElementById('locationCoords').textContent = 
                    `Lat: ${selectedLat.toFixed(6)}, Lng: ${selectedLng.toFixed(6)}`;
                document.getElementById('selectedLocation').style.display = 'block';
                document.getElementById('continueBtn').disabled = false;
            });
    }, 2500);
});

// Location search (Turkey cities)
const searchInput = document.getElementById('locationSearch');
let searchTimeout;

searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const query = this.value.trim();
    
    if (query.length < 2) return;
    
    searchTimeout = setTimeout(() => {
        // Search within Turkey
        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)},Turkey&countrycodes=tr`)
            .then(res => res.json())
            .then(data => {
                if (data.length > 0) {
                    const result = data[0];
                    const lat = parseFloat(result.lat);
                    const lng = parseFloat(result.lon);
                    
                    map.flyTo({ center: [lng, lat], zoom: 10, duration: 1500 });
                    setTimeout(() => {
                        map.fire('click', { latlng: { lat, lng } });
                    }, 1600);
                }
            })
            .catch(err => console.error('Search error:', err));
    }, 500);
});

// Wizard navigation
function nextStep(stepNumber) {
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.classList.remove('active');
    });
    
    document.getElementById(`step${stepNumber}`).classList.add('active');
    
    document.querySelectorAll('.progress-step').forEach(step => {
        const num = parseInt(step.getAttribute('data-step'));
        step.classList.remove('active', 'completed');
        
        if (num < stepNumber) {
            step.classList.add('completed');
        } else if (num === stepNumber) {
            step.classList.add('active');
        }
    });
    
    // Update preview on step 3
    if (stepNumber === 3) {
        const title = document.getElementById('capsuleTitle').value || 'Kapsül İsmi';
        const dateInput = document.getElementById('unlockDate').value;
        let dateText = 'Açılış Tarihi';
        
        if (dateInput) {
            const date = new Date(dateInput);
            dateText = date.toLocaleDateString('tr-TR', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
        }
        
        document.getElementById('previewTitle').textContent = title;
        document.getElementById('previewDate').textContent = dateText;
    }
    
    // Update payment info on step 4
    if (stepNumber === 4) {
        document.getElementById('paymentPrice').textContent = `₺${PRICE}`;
        document.getElementById('paymentTotal').textContent = `₺${PRICE}`;
        document.getElementById('paymentZone').textContent = 'Türkiye';
        document.getElementById('paymentLocation').textContent = selectedLocationName || '-';
        document.getElementById('paymentTitle').textContent = document.getElementById('capsuleTitle').value || '-';
    }
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function prevStep(stepNumber) {
    nextStep(stepNumber);
}

// Add CSS for user marker and shovel animation
const style = document.createElement('style');
style.textContent = `
    /* User Dot Marker */
    .user-dot-marker {
        width: 24px;
        height: 24px;
        cursor: pointer;
        position: relative;
    }
    
    .user-dot-inner {
        width: 16px;
        height: 16px;
        background: linear-gradient(135deg, #ff6b9d, #ffa94d);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        box-shadow: 0 0 20px rgba(255, 107, 157, 0.8);
        animation: pulse-user 2s ease-in-out infinite;
    }
    
    @keyframes pulse-user {
        0%, 100% {
            box-shadow: 0 0 20px rgba(255, 107, 157, 0.8);
        }
        50% {
            box-shadow: 0 0 35px rgba(255, 107, 157, 1);
        }
    }
    
    .user-dot-ring {
        width: 24px;
        height: 24px;
        border: 3px solid rgba(255, 107, 157, 0.5);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        animation: ring-user 2s ease-in-out infinite;
    }
    
    @keyframes ring-user {
        0%, 100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
        }
        50% {
            transform: translate(-50%, -50%) scale(1.6);
            opacity: 0.2;
        }
    }
    
    /* Shovel Animation Overlay */
    .dig-animation-overlay .shovel {
        font-size: 10rem;
        animation: digShovel 3s ease-in-out;
    }
    
    @keyframes digShovel {
        0% { 
            transform: translateY(-150px) rotate(-60deg); 
            opacity: 0;
        }
        15% {
            transform: translateY(-50px) rotate(-45deg);
            opacity: 1;
        }
        35% { 
            transform: translateY(0) rotate(-20deg); 
        }
        50% { 
            transform: translateY(30px) rotate(10deg); 
        }
        60% {
            transform: translateY(20px) rotate(-5deg);
        }
        70% {
            transform: translateY(0) rotate(-10deg);
        }
        85% {
            transform: translateY(-100px) rotate(-50deg);
            opacity: 1;
        }
        100% { 
            transform: translateY(-200px) rotate(-70deg) scale(0.3); 
            opacity: 0;
        }
    }
    
    .dig-animation-overlay .dirt-particles {
        animation: showDirt 3s ease-in-out;
    }
    
    @keyframes showDirt {
        0%, 30% { opacity: 0; }
        40% { opacity: 1; }
        80% { opacity: 1; }
        100% { opacity: 0; }
    }
    
    .dig-animation-overlay .dirt:nth-child(1) {
        animation: flyDirtLeft 1.5s ease-out;
        animation-delay: 1.2s;
    }
    
    .dig-animation-overlay .dirt:nth-child(2) {
        animation: flyDirtUp 1.5s ease-out;
        animation-delay: 1.3s;
    }
    
    .dig-animation-overlay .dirt:nth-child(3) {
        animation: flyDirtRight 1.5s ease-out;
        animation-delay: 1.4s;
    }
    
    @keyframes flyDirtLeft {
        0% { transform: translate(0, 0) scale(1); opacity: 1; }
        100% { transform: translate(-120px, -80px) scale(0.3); opacity: 0; }
    }
    
    @keyframes flyDirtUp {
        0% { transform: translate(0, 0) scale(1); opacity: 1; }
        100% { transform: translate(0, -120px) scale(0.3); opacity: 0; }
    }
    
    @keyframes flyDirtRight {
        0% { transform: translate(0, 0) scale(1); opacity: 1; }
        100% { transform: translate(120px, -80px) scale(0.3); opacity: 0; }
    }
    
    .dig-animation-overlay .dig-text {
        animation: pulseDig 3s ease-in-out;
    }
    
    @keyframes pulseDig {
        0%, 100% { opacity: 0; }
        20%, 80% { opacity: 1; }
        40% { transform: scale(1.05); }
        60% { transform: scale(0.95); }
    }
`;
document.head.appendChild(style);

console.log('Turkey-focused create page initialized with shovel animation!');
