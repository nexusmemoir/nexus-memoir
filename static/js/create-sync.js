// Create Wizard - Complete with Mock Payment
(() => {
    if (window.__CREATE_SYNC_LOADED__) return;
    window.__CREATE_SYNC_LOADED__ = true;

    mapboxgl.accessToken = 'pk.eyJ1IjoibmV4dXNtZW1vaXIiLCJhIjoiY21rczVsbnpiMTZuejNjcXk4M2Q4c2Z4bSJ9.Itm0AFzYPjurF_IBe_GNpQ';

    const PRICE = 499;
    let selectedLat = null;
    let selectedLng = null;
    let selectedLocationName = '';
    let userMarker = null;
    let tapCount = 0;
    let tapTimer = null;

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
                { id: 'background', type: 'background', paint: { 'background-color': '#f5e6ff' } },
                { id: 'carto-tiles', type: 'raster', source: 'carto-light', paint: { 'raster-opacity': 0.9 } }
            ]
        },
        center: [20, 30],
        zoom: 2.5,
        minZoom: 2,
        maxZoom: 18
    });

    map.addControl(new mapboxgl.NavigationControl());

    function createUserDotMarker() {
        const el = document.createElement('div');
        el.style.cssText = 'width:24px;height:24px;position:relative;';
        el.innerHTML = '<div style="width:16px;height:16px;background:linear-gradient(135deg,#ff6b9d,#ffa94d);border-radius:50%;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);box-shadow:0 0 20px rgba(255,107,157,0.8);"></div>';
        return el;
    }

    function playShovelAnimation() {
        const overlay = document.getElementById('digAnimation');
        overlay.style.display = 'flex';
        setTimeout(() => { overlay.style.display = 'none'; }, 3000);
    }

    function digCapsule(lat, lng) {
        selectedLat = lat;
        selectedLng = lng;
        
        playShovelAnimation();
        if (userMarker) userMarker.remove();
        
        setTimeout(() => {
            const el = createUserDotMarker();
            userMarker = new mapboxgl.Marker({ element: el, anchor: 'center' }).setLngLat([lng, lat]).addTo(map);
            
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
                .then(res => res.json())
                .then(data => {
                    const city = data.address.city || data.address.town || data.address.village || data.address.county || data.address.state;
                    const country = data.address.country;
                    selectedLocationName = city ? `${city}, ${country}` : (country || 'Seçilen Lokasyon');
                    
                    document.getElementById('locationName').textContent = selectedLocationName;
                    document.getElementById('locationCoords').textContent = `Lat: ${lat.toFixed(6)}, Lng: ${lng.toFixed(6)}`;
                    document.getElementById('selectedLocation').style.display = 'block';
                    document.getElementById('continueBtn').disabled = false;
                })
                .catch(() => {
                    selectedLocationName = 'Seçilen Lokasyon';
                    document.getElementById('locationName').textContent = selectedLocationName;
                    document.getElementById('locationCoords').textContent = `Lat: ${lat.toFixed(6)}, Lng: ${lng.toFixed(6)}`;
                    document.getElementById('selectedLocation').style.display = 'block';
                    document.getElementById('continueBtn').disabled = false;
                });
        }, 2500);
    }

    // Desktop: double-click
    map.on('dblclick', (e) => {
        e.preventDefault();
        tapCount = 0;
        clearTimeout(tapTimer);
        digCapsule(e.lngLat.lat, e.lngLat.lng);
    });

    // Mobile: 3 taps
    map.on('click', (e) => {
        tapCount++;
        if (tapCount === 3) {
            clearTimeout(tapTimer);
            tapCount = 0;
            digCapsule(e.lngLat.lat, e.lngLat.lng);
        } else {
            clearTimeout(tapTimer);
            tapTimer = setTimeout(() => { tapCount = 0; }, 500);
        }
    });

    // Search
    const searchInput = document.getElementById('locationSearch');
    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        if (query.length < 2) return;
        
        searchTimeout = setTimeout(() => {
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.length > 0) {
                        const lat = parseFloat(data[0].lat);
                        const lng = parseFloat(data[0].lon);
                        map.flyTo({ center: [lng, lat], zoom: 12, duration: 1500 });
                    }
                })
                .catch(err => console.error('Search error:', err));
        }, 500);
    });

    // Wizard navigation
    window.nextStep = function(stepNumber) {
        document.querySelectorAll('.wizard-step').forEach(s => s.classList.remove('active'));
        document.getElementById(`step${stepNumber}`).classList.add('active');
        
        document.querySelectorAll('.progress-step').forEach(s => {
            const num = parseInt(s.getAttribute('data-step'));
            s.classList.remove('active', 'completed');
            if (num < stepNumber) s.classList.add('completed');
            else if (num === stepNumber) s.classList.add('active');
        });
        
        if (stepNumber === 3) {
            document.getElementById('previewTitle').textContent = document.getElementById('capsuleTitle').value || 'Anı Kapsülü';
            const dateInput = document.getElementById('unlockDate').value;
            if (dateInput) {
                const date = new Date(dateInput);
                document.getElementById('previewDate').textContent = date.toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' });
            }
        }
        
        if (stepNumber === 4) {
            document.getElementById('paymentTotal').textContent = `₺${PRICE}`;
            document.getElementById('paymentLocation').textContent = selectedLocationName || '-';
            document.getElementById('paymentTitle').textContent = document.getElementById('capsuleTitle').value || '-';
        }
        
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.prevStep = function(stepNumber) {
        window.nextStep(stepNumber);
    };

    // Mock Payment - Direct API Call with Burial Animation
    window.completePurchase = async function() {
        const title = document.getElementById('capsuleTitle').value;
        const unlockDate = document.getElementById('unlockDate').value;
        
        if (!title || !unlockDate || !selectedLat || !selectedLng) {
            alert('Lütfen tüm alanları doldurun');
            return;
        }
        
        const button = event.target;
        button.disabled = true;
        button.textContent = 'Ödeme işleniyor...';
        
        try {
            // Simulate payment processing (2 seconds)
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Show burial animation
            button.textContent = 'Kapsül gömülüyor...';
            const overlay = document.getElementById('digAnimation');
            if (overlay) {
                overlay.style.display = 'flex';
                // Update animation text
                const digText = overlay.querySelector('.dig-text');
                if (digText) digText.textContent = 'Anı kapsülünüz gömülüyor...';
            }
            
            // Create FormData
            const formData = new FormData();
            formData.append('lat', selectedLat);
            formData.append('lng', selectedLng);
            formData.append('title', title);
            formData.append('unlock_at', unlockDate);
            formData.append('location_name', selectedLocationName);
            
            const response = await fetch('/api/capsules/create', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update animation text to success
                if (overlay) {
                    const digText = overlay.querySelector('.dig-text');
                    if (digText) digText.textContent = '✅ Kapsül başarıyla gömüldü!';
                    const shovel = overlay.querySelector('.shovel');
                    if (shovel) shovel.textContent = '🎉';
                }
                
                // Wait for animation then redirect
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Redirect to success page
                window.location.href = `/success?token=${encodeURIComponent(data.token)}&pin=${encodeURIComponent(data.pin)}&qr=${encodeURIComponent(data.qr_code)}`;
            } else {
                if (overlay) overlay.style.display = 'none';
                alert('Hata: ' + (data.error || 'Bilinmeyen hata'));
                button.disabled = false;
                button.textContent = 'Ödemeyi Tamamla';
            }
        } catch (error) {
            console.error('Error:', error);
            const overlay = document.getElementById('digAnimation');
            if (overlay) overlay.style.display = 'none';
            alert('Bağlantı hatası');
            button.disabled = false;
            button.textContent = 'Ödemeyi Tamamla';
        }
    };

    console.log('Create wizard ready (3-tap mobile, double-click desktop)');
})();
