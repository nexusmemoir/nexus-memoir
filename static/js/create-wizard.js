// Create Capsule Wizard

let selectedLat = null;
let selectedLng = null;
let selectedLocationName = '';
let marker = null;

// Initialize Leaflet map
const map = L.map('map').setView([41.0082, 28.9784], 10); // Istanbul default

// Use CartoDB dark theme
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    maxZoom: 19
}).addTo(map);

// Custom marker icon
const customIcon = L.divIcon({
    className: 'custom-marker',
    html: '<div style="background: linear-gradient(135deg, #6366f1, #ec4899); width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 20px rgba(99, 102, 241, 0.8); animation: pulse 2s infinite;"></div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
});

// Map click handler
map.on('click', function(e) {
    selectedLat = e.latlng.lat;
    selectedLng = e.latlng.lng;
    
    // Remove existing marker
    if (marker) {
        map.removeLayer(marker);
    }
    
    // Add new marker
    marker = L.marker([selectedLat, selectedLng], { icon: customIcon }).addTo(map);
    
    // Reverse geocode to get location name
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${selectedLat}&lon=${selectedLng}`)
        .then(res => res.json())
        .then(data => {
            const city = data.address.city || data.address.town || data.address.village || data.address.state;
            const country = data.address.country;
            selectedLocationName = city ? `${city}, ${country}` : country || 'Bilinmeyen Lokasyon';
            
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
});

// Location search
const searchInput = document.getElementById('locationSearch');
let searchTimeout;

searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const query = this.value.trim();
    
    if (query.length < 3) return;
    
    searchTimeout = setTimeout(() => {
        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                if (data.length > 0) {
                    const result = data[0];
                    const lat = parseFloat(result.lat);
                    const lng = parseFloat(result.lon);
                    
                    // Fly to location
                    map.flyTo([lat, lng], 12, {
                        duration: 1.5
                    });
                    
                    // Simulate click
                    setTimeout(() => {
                        map.fire('click', {
                            latlng: L.latLng(lat, lng)
                        });
                    }, 1600);
                }
            })
            .catch(err => console.error('Search error:', err));
    }, 500);
});

// Wizard navigation
function nextStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.classList.remove('active');
    });
    
    // Show target step
    document.getElementById(`step${stepNumber}`).classList.add('active');
    
    // Update progress
    document.querySelectorAll('.progress-step').forEach(step => {
        const num = parseInt(step.getAttribute('data-step'));
        step.classList.remove('active', 'completed');
        
        if (num < stepNumber) {
            step.classList.add('completed');
        } else if (num === stepNumber) {
            step.classList.add('active');
        }
    });
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function prevStep(stepNumber) {
    nextStep(stepNumber);
}

// Add CSS for pulse animation
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
            opacity: 1;
        }
        50% {
            transform: scale(1.2);
            opacity: 0.8;
        }
    }
`;
document.head.appendChild(style);

// Save form data to localStorage
function saveFormData() {
    const data = {
        lat: selectedLat,
        lng: selectedLng,
        locationName: selectedLocationName,
        capsuleTitle: document.getElementById('capsuleTitle')?.value,
        unlockDate: document.getElementById('unlockDate')?.value
    };
    localStorage.setItem('capsuleData', JSON.stringify(data));
}

// Auto-save on input
document.addEventListener('input', saveFormData);

console.log('Create wizard initialized');
