// Create Capsule Wizard with Zone Pricing

// ZONE DEFINITIONS
const zones = {
    premium: {
        name: "Premium Zone",
        price: 1500,
        color: "#ef4444",
        cities: [
            { lat: 41.0082, lng: 28.9784, name: "Istanbul", country: "Turkey" },
            { lat: 39.9334, lng: 32.8597, name: "Ankara", country: "Turkey" },
            { lat: 48.8566, lng: 2.3522, name: "Paris", country: "France" },
            { lat: 51.5074, lng: -0.1278, name: "London", country: "UK" },
            { lat: 40.7128, lng: -74.0060, name: "New York", country: "USA" },
            { lat: 35.6762, lng: 139.6503, name: "Tokyo", country: "Japan" },
            { lat: 25.2048, lng: 55.2708, name: "Dubai", country: "UAE" },
            { lat: 34.0522, lng: -118.2437, name: "Los Angeles", country: "USA" },
            { lat: -33.8688, lng: 151.2093, name: "Sydney", country: "Australia" },
            { lat: 55.7558, lng: 37.6173, name: "Moscow", country: "Russia" }
        ]
    },
    popular: {
        name: "Popular Zone",
        price: 999,
        color: "#f59e0b",
        cities: [
            { lat: 38.4237, lng: 27.1428, name: "Izmir", country: "Turkey" },
            { lat: 36.8969, lng: 30.7133, name: "Antalya", country: "Turkey" },
            { lat: 40.1826, lng: 29.0670, name: "Bursa", country: "Turkey" },
            { lat: 52.5200, lng: 13.4050, name: "Berlin", country: "Germany" },
            { lat: 41.9028, lng: 12.4964, name: "Rome", country: "Italy" },
            { lat: 40.4168, lng: -3.7038, name: "Madrid", country: "Spain" },
            { lat: 52.3676, lng: 4.9041, name: "Amsterdam", country: "Netherlands" },
            { lat: 13.7563, lng: 100.5018, name: "Bangkok", country: "Thailand" },
            { lat: 1.3521, lng: 103.8198, name: "Singapore", country: "Singapore" },
            { lat: 37.5665, lng: 126.9780, name: "Seoul", country: "South Korea" },
            { lat: 45.4642, lng: 9.1900, name: "Milan", country: "Italy" },
            { lat: 59.3293, lng: 18.0686, name: "Stockholm", country: "Sweden" },
            { lat: 50.0755, lng: 14.4378, name: "Prague", country: "Czech Republic" },
            { lat: 55.6761, lng: 12.5683, name: "Copenhagen", country: "Denmark" },
            { lat: 22.3193, lng: 114.1694, name: "Hong Kong", country: "China" }
        ]
    },
    standard: {
        name: "Standard Zone",
        price: 699,
        color: "#eab308",
        cities: [
            { lat: 37.0000, lng: 35.3213, name: "Adana", country: "Turkey" },
            { lat: 37.8667, lng: 32.4833, name: "Konya", country: "Turkey" },
            { lat: 37.0660, lng: 37.3781, name: "Gaziantep", country: "Turkey" },
            { lat: 38.4192, lng: 27.1287, name: "Izmir", country: "Turkey" },
            { lat: 48.2082, lng: 16.3738, name: "Vienna", country: "Austria" },
            { lat: 37.9838, lng: 23.7275, name: "Athens", country: "Greece" },
            { lat: 38.7223, lng: -9.1393, name: "Lisbon", country: "Portugal" },
            { lat: 47.4979, lng: 19.0402, name: "Budapest", country: "Hungary" },
            { lat: 50.4501, lng: 30.5234, name: "Kyiv", country: "Ukraine" },
            { lat: 52.2297, lng: 21.0122, name: "Warsaw", country: "Poland" },
            { lat: 41.3275, lng: 19.8187, name: "Tirana", country: "Albania" },
            { lat: 44.4268, lng: 26.1025, name: "Bucharest", country: "Romania" },
            { lat: 42.6977, lng: 23.3219, name: "Sofia", country: "Bulgaria" },
            { lat: 45.8150, lng: 15.9819, name: "Zagreb", country: "Croatia" },
            { lat: 40.1872, lng: 44.5152, name: "Yerevan", country: "Armenia" },
            { lat: 41.7151, lng: 44.8271, name: "Tbilisi", country: "Georgia" },
            { lat: 39.9042, lng: 116.4074, name: "Beijing", country: "China" },
            { lat: 31.2304, lng: 121.4737, name: "Shanghai", country: "China" },
            { lat: 28.6139, lng: 77.2090, name: "New Delhi", country: "India" },
            { lat: 19.0760, lng: 72.8777, name: "Mumbai", country: "India" }
        ]
    },
    basic: {
        name: "Basic Zone",
        price: 499,
        color: "#22c55e",
        cities: [] // Everywhere else
    }
};

let selectedLat = null;
let selectedLng = null;
let selectedLocationName = '';
let selectedZone = null;
let marker = null;
let zoneCircles = [];

// Initialize Leaflet map with watercolor style
const map = L.map('map', {
    zoomControl: true,
    minZoom: 2,
    maxZoom: 18
}).setView([41.0082, 28.9784], 3);

// Watercolor base (more cute!)
L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; Stadia Maps &copy; OpenStreetMap',
    maxZoom: 19
}).addTo(map);

// Draw zone circles
function drawZoneCirlces() {
    // Clear existing
    zoneCircles.forEach(circle => map.removeLayer(circle));
    zoneCircles = [];
    
    // Draw all zones
    Object.values(zones).forEach(zone => {
        if (zone.cities.length === 0) return; // Skip basic (it's everywhere)
        
        zone.cities.forEach(city => {
            const circle = L.circle([city.lat, city.lng], {
                radius: 150000, // 150km radius
                color: zone.color,
                fillColor: zone.color,
                fillOpacity: 0.15,
                weight: 2,
                opacity: 0.6
            }).addTo(map);
            
            // Tooltip
            circle.bindTooltip(`
                <div style="font-weight: 600;">${city.name}</div>
                <div style="font-size: 0.875rem; color: #94a3b8;">${zone.name}</div>
                <div style="font-weight: 700; color: ${zone.color};">₺${zone.price}</div>
            `, {
                permanent: false,
                direction: 'top'
            });
            
            zoneCircles.push(circle);
        });
    });
}

drawZoneCirlces();

// Determine zone from coordinates
function getZoneByCoordinates(lat, lng) {
    let closestZone = zones.basic;
    let minDistance = Infinity;
    
    // Check all zones
    for (const [key, zone] of Object.entries(zones)) {
        if (zone.cities.length === 0) continue;
        
        zone.cities.forEach(city => {
            const distance = Math.sqrt(
                Math.pow(lat - city.lat, 2) + 
                Math.pow(lng - city.lng, 2)
            );
            
            // If within 150km (approx 1.35 degrees)
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

// Custom cute marker icon
const cuteMarker = L.divIcon({
    className: 'cute-marker',
    html: `
        <div style="
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            width: 32px;
            height: 32px;
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            border: 3px solid white;
            box-shadow: 0 4px 20px rgba(251, 191, 36, 0.8);
            animation: bounce 1s ease-in-out infinite;
            position: relative;
        ">
            <div style="
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(45deg);
                font-size: 16px;
            ">📍</div>
        </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32]
});

// Map click handler
map.on('click', function(e) {
    selectedLat = e.latlng.lat;
    selectedLng = e.latlng.lng;
    
    // Determine zone
    const zone = getZoneByCoordinates(selectedLat, selectedLng);
    updateZoneInfo(zone);
    
    // Remove existing marker
    if (marker) {
        map.removeLayer(marker);
    }
    
    // Add new marker
    marker = L.marker([selectedLat, selectedLng], { icon: cuteMarker }).addTo(map);
    
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
});

// Location search
const searchInput = document.getElementById('locationSearch');
let searchTimeout;

searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const query = this.value.trim();
    
    if (query.length < 2) return;
    
    searchTimeout = setTimeout(() => {
        // First check if it's in our zones
        let found = false;
        
        for (const zone of Object.values(zones)) {
            const city = zone.cities.find(c => 
                c.name.toLowerCase().includes(query.toLowerCase())
            );
            
            if (city) {
                map.flyTo([city.lat, city.lng], 10, { duration: 1.5 });
                setTimeout(() => {
                    map.fire('click', { latlng: L.latLng(city.lat, city.lng) });
                }, 1600);
                found = true;
                break;
            }
        }
        
        // If not in zones, use geocoding
        if (!found) {
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.length > 0) {
                        const result = data[0];
                        const lat = parseFloat(result.lat);
                        const lng = parseFloat(result.lon);
                        
                        map.flyTo([lat, lng], 12, { duration: 1.5 });
                        setTimeout(() => {
                            map.fire('click', { latlng: L.latLng(lat, lng) });
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
    
    // Update payment info when reaching step 4
    if (stepNumber === 4 && selectedZone) {
        document.getElementById('paymentPrice').textContent = `₺${selectedZone.price}`;
        document.getElementById('paymentTotal').textContent = `₺${selectedZone.price}`;
        document.getElementById('paymentZone').textContent = selectedZone.name;
        document.getElementById('paymentLocation').textContent = selectedLocationName || '-';
    }
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function prevStep(stepNumber) {
    nextStep(stepNumber);
}

// Add bounce animation
const style = document.createElement('style');
style.textContent = `
    @keyframes bounce {
        0%, 100% {
            transform: translateY(0) rotate(-45deg);
        }
        50% {
            transform: translateY(-10px) rotate(-45deg);
        }
    }
`;
document.head.appendChild(style);

// Save form data
function saveFormData() {
    const data = {
        lat: selectedLat,
        lng: selectedLng,
        locationName: selectedLocationName,
        zone: selectedZone,
        capsuleTitle: document.getElementById('capsuleTitle')?.value,
        unlockDate: document.getElementById('unlockDate')?.value
    };
    localStorage.setItem('capsuleData', JSON.stringify(data));
}

document.addEventListener('input', saveFormData);

console.log('Zone-based wizard initialized - 4 zones with dynamic pricing!');
