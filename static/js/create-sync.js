// Create Page Sync - Mapbox + Dig Animation + Zone System

// Mapbox token
mapboxgl.accessToken = 'pk.eyJ1IjoibmV4dXNtZW1vaXIiLCJhIjoiY21rb2sycXN4MDhnMTNjc2FxYWtxaXY1byJ9.PEZQ7jJ02OJZ0ndCVEcc8g';

// Zone definitions (same as landing)
const zones = {
    premium: {
        name: "Premium Zone",
        price: 1500,
        color: "#ff6b9d",
        cities: [
            { lat: 41.0082, lng: 28.9784, name: "Istanbul" },
            { lat: 39.9334, lng: 32.8597, name: "Ankara" },
            { lat: 48.8566, lng: 2.3522, name: "Paris" },
            { lat: 51.5074, lng: -0.1278, name: "London" },
            { lat: 40.7128, lng: -74.0060, name: "New York" },
            { lat: 35.6762, lng: 139.6503, name: "Tokyo" },
            { lat: 25.2048, lng: 55.2708, name: "Dubai" },
            { lat: 34.0522, lng: -118.2437, name: "Los Angeles" },
            { lat: -33.8688, lng: 151.2093, name: "Sydney" },
            { lat: 55.7558, lng: 37.6173, name: "Moscow" }
        ]
    },
    popular: {
        name: "Popular Zone",
        price: 999,
        color: "#ffa94d",
        cities: [
            { lat: 38.4237, lng: 27.1428, name: "Izmir" },
            { lat: 36.8969, lng: 30.7133, name: "Antalya" },
            { lat: 40.1826, lng: 29.0670, name: "Bursa" },
            { lat: 52.5200, lng: 13.4050, name: "Berlin" },
            { lat: 41.9028, lng: 12.4964, name: "Rome" },
            { lat: 40.4168, lng: -3.7038, name: "Madrid" },
            { lat: 52.3676, lng: 4.9041, name: "Amsterdam" },
            { lat: 13.7563, lng: 100.5018, name: "Bangkok" },
            { lat: 1.3521, lng: 103.8198, name: "Singapore" },
            { lat: 37.5665, lng: 126.9780, name: "Seoul" }
        ]
    },
    standard: {
        name: "Standard Zone",
        price: 699,
        color: "#ffd93d",
        cities: [
            { lat: 37.0000, lng: 35.3213, name: "Adana" },
            { lat: 37.8667, lng: 32.4833, name: "Konya" },
            { lat: 37.0660, lng: 37.3781, name: "Gaziantep" },
            { lat: 48.2082, lng: 16.3738, name: "Vienna" },
            { lat: 37.9838, lng: 23.7275, name: "Athens" },
            { lat: 38.7223, lng: -9.1393, name: "Lisbon" },
            { lat: 47.4979, lng: 19.0402, name: "Budapest" }
        ]
    },
    basic: {
        name: "Basic Zone",
        price: 499,
        color: "#95e1d3",
        cities: []
    }
};

let selectedLat = null;
let selectedLng = null;
let selectedLocationName = '';
let selectedZone = null;
let userMarker = null;

// Initialize map (same style as landing)
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
                    'raster-opacity': 0.85
                }
            }
        ]
    },
    center: [20, 30],
    zoom: 3,
    minZoom: 2,
    maxZoom: 18
});

// Add controls
map.addControl(new mapboxgl.NavigationControl());

// Determine zone from coordinates
function getZoneByCoordinates(lat, lng) {
    let closestZone = zones.basic;
    let minDistance = Infinity;
    
    for (const [key, zone] of Object.entries(zones)) {
        if (zone.cities.length === 0) continue;
        
        zone.cities.forEach(city => {
            const distance = Math.sqrt(
                Math.pow(lat - city.lat, 2) + 
                Math.pow(lng - city.lng, 2)
            );
            
            if (distance < 1.35 && distance < minDistance) {
                minDistance = distance;
                closestZone = zone;
            }
        });
    }
    
    return closestZone;
}

// Update zone info display
function updateZoneInfo(zone) {
    document.getElementById('currentZoneName').textContent = zone.name;
    document.getElementById('currentZonePrice').textContent = `₺${zone.price}`;
    selectedZone = zone;
}

// Create balloon marker HTML
function createBalloonMarkerHTML(title, date, zone) {
    return `
        <div class="user-balloon-marker" style="border-color: ${zone.color};">
            <div class="user-balloon-content">
                <div class="user-balloon-title">${title || 'Kapsülün'}</div>
                <div class="user-balloon-date">${date || 'Tarih belirle'}</div>
                <div class="user-balloon-status">🔒 Kilitli</div>
            </div>
            <div class="user-balloon-pointer" style="border-top-color: ${zone.color};"></div>
            <div class="user-balloon-pin" style="background: ${zone.color};"></div>
        </div>
    `;
}

// Dig animation
function playDigAnimation() {
    const overlay = document.getElementById('digAnimation');
    overlay.style.display = 'flex';
    
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 2000);
}

// Map click handler with dig animation
map.on('click', function(e) {
    selectedLat = e.latlng.lat;
    selectedLng = e.latlng.lng;
    
    // Play dig animation
    playDigAnimation();
    
    // Determine zone
    const zone = getZoneByCoordinates(selectedLat, selectedLng);
    updateZoneInfo(zone);
    
    // Remove existing marker
    if (userMarker) {
        userMarker.remove();
    }
    
    // Wait for dig animation to finish
    setTimeout(() => {
        // Add balloon marker
        const el = document.createElement('div');
        el.innerHTML = createBalloonMarkerHTML('Senin Kapsülün', 'Tarih belirle', zone);
        
        userMarker = new mapboxgl.Marker({
            element: el,
            anchor: 'bottom'
        })
        .setLngLat([selectedLng, selectedLat])
        .addTo(map);
        
        // Reverse geocode
        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${selectedLat}&lon=${selectedLng}`)
            .then(res => res.json())
            .then(data => {
                const city = data.address.city || data.address.town || data.address.village || data.address.state;
                const country = data.address.country;
                selectedLocationName = city ? `${city}, ${country}` : country || 'Selected Location';
                
                document.getElementById('locationName').textContent = selectedLocationName;
                document.getElementById('locationCoords').textContent = 
                    `Lat: ${selectedLat.toFixed(6)}, Lng: ${selectedLng.toFixed(6)} • ${zone.name}`;
                document.getElementById('selectedLocation').style.display = 'block';
                document.getElementById('continueBtn').disabled = false;
            })
            .catch(err => {
                console.error('Geocoding error:', err);
                selectedLocationName = 'Selected Location';
                document.getElementById('locationName').textContent = selectedLocationName;
                document.getElementById('locationCoords').textContent = 
                    `Lat: ${selectedLat.toFixed(6)}, Lng: ${selectedLng.toFixed(6)} • ${zone.name}`;
                document.getElementById('selectedLocation').style.display = 'block';
                document.getElementById('continueBtn').disabled = false;
            });
    }, 1500);
});

// Location search
const searchInput = document.getElementById('locationSearch');
let searchTimeout;

searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const query = this.value.trim();
    
    if (query.length < 2) return;
    
    searchTimeout = setTimeout(() => {
        let found = false;
        
        for (const zone of Object.values(zones)) {
            const city = zone.cities.find(c => 
                c.name.toLowerCase().includes(query.toLowerCase())
            );
            
            if (city) {
                map.flyTo({ center: [city.lng, city.lat], zoom: 10, duration: 1500 });
                setTimeout(() => {
                    map.fire('click', { latlng: { lat: city.lat, lng: city.lng } });
                }, 1600);
                found = true;
                break;
            }
        }
        
        if (!found) {
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.length > 0) {
                        const result = data[0];
                        const lat = parseFloat(result.lat);
                        const lng = parseFloat(result.lon);
                        
                        map.flyTo({ center: [lng, lat], zoom: 12, duration: 1500 });
                        setTimeout(() => {
                            map.fire('click', { latlng: { lat, lng } });
                        }, 1600);
                    }
                })
                .catch(err => console.error('Search error:', err));
        }
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
        
        // Update balloon border color
        const previewBalloon = document.querySelector('.preview-balloon');
        if (selectedZone) {
            previewBalloon.style.borderColor = selectedZone.color;
            document.querySelector('.preview-balloon-pointer').style.borderTopColor = selectedZone.color;
            document.querySelector('.preview-balloon-pin').style.background = selectedZone.color;
        }
    }
    
    // Update payment info on step 4
    if (stepNumber === 4 && selectedZone) {
        document.getElementById('paymentPrice').textContent = `₺${selectedZone.price}`;
        document.getElementById('paymentTotal').textContent = `₺${selectedZone.price}`;
        document.getElementById('paymentZone').textContent = selectedZone.name;
        document.getElementById('paymentLocation').textContent = selectedLocationName || '-';
        document.getElementById('paymentTitle').textContent = document.getElementById('capsuleTitle').value || '-';
    }
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function prevStep(stepNumber) {
    nextStep(stepNumber);
}

// Add CSS for user balloon markers
const style = document.createElement('style');
style.textContent = `
    .user-balloon-marker {
        background: white;
        padding: 12px 16px;
        border-radius: 16px;
        border: 3px solid;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        min-width: 180px;
        animation: float 3s ease-in-out infinite;
        cursor: pointer;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
    }
    
    .user-balloon-content {
        position: relative;
        z-index: 2;
    }
    
    .user-balloon-title {
        font-size: 14px;
        font-weight: 700;
        color: #0f0f23;
        margin-bottom: 4px;
    }
    
    .user-balloon-date {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 6px;
    }
    
    .user-balloon-status {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        background: rgba(255, 255, 255, 0.8);
        padding: 4px 8px;
        border-radius: 8px;
        display: inline-block;
    }
    
    .user-balloon-pointer {
        position: absolute;
        bottom: -12px;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 12px solid transparent;
        border-right: 12px solid transparent;
        border-top: 12px solid;
    }
    
    .user-balloon-pin {
        position: absolute;
        bottom: -32px;
        left: 50%;
        width: 12px;
        height: 20px;
        border-radius: 50% 50% 50% 0;
        transform: translateX(-50%) rotate(-45deg);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
`;
document.head.appendChild(style);

console.log('Create page sync initialized - Mapbox + dig animation + zones!');
