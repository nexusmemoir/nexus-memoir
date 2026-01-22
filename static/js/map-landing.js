// Map Landing - Real Capsules from API
mapboxgl.accessToken = 'pk.eyJ1IjoibmV4dXNtZW1vaXIiLCJhIjoiY21rb2sycXN4MDhnMTNjc2FxYWtxaXY1byJ9.PEZQ7jJ02OJZ0ndCVEcc8g';

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

function createPopupContent(capsule) {
    const icon = capsule.status === 'locked' ? '🔒' : '🎉';
    const statusText = capsule.status === 'locked' ? 'Kilitli' : 'Açıldı';
    
    return `
        <div style="padding: 8px 12px; min-width: 180px;">
            <div style="font-size: 15px; font-weight: 700; color: #0f0f23; margin-bottom: 6px;">${capsule.title}</div>
            <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">📍 ${capsule.city}</div>
            <div style="font-size: 13px; color: #64748b; margin-bottom: 8px;">🎁 ${capsule.unlock_at}</div>
            <div style="font-size: 12px; font-weight: 600; color: white; background: linear-gradient(135deg, #ff6b9d, #ffa94d); padding: 5px 10px; border-radius: 8px; display: inline-block;">${icon} ${statusText}</div>
        </div>
    `;
}

map.on('load', async function() {
    try {
        const response = await fetch('/api/capsules/public');
        const data = await response.json();
        
        if (data.capsules && data.capsules.length > 0) {
            data.capsules.forEach(capsule => {
                const el = document.createElement('div');
                el.className = 'stable-dot-marker';
                el.style.cssText = 'width:20px;height:20px;cursor:pointer;position:relative;transition:transform 0.2s;';
                el.innerHTML = '<div style="width:12px;height:12px;background:linear-gradient(135deg,#ff6b9d,#ffa94d);border-radius:50%;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);box-shadow:0 0 15px rgba(255,107,157,0.8);animation:pulse-core 2s ease-in-out infinite;"></div><div style="width:20px;height:20px;border:2px solid rgba(255,107,157,0.4);border-radius:50%;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);animation:ring-pulse 2s ease-in-out infinite;pointer-events:none;"></div>';
                
                const popup = new mapboxgl.Popup({
                    offset: 25,
                    closeButton: true,
                    closeOnClick: true,
                    maxWidth: '300px'
                }).setHTML(createPopupContent(capsule));
                
                const marker = new mapboxgl.Marker({
                    element: el,
                    anchor: 'center'
                })
                .setLngLat([capsule.lng, capsule.lat])
                .addTo(map);
                
                el.addEventListener('mouseenter', () => {
                    el.style.transform = 'scale(1.3)';
                    el.style.zIndex = '10';
                });
                
                el.addEventListener('mouseleave', () => {
                    el.style.transform = 'scale(1)';
                    el.style.zIndex = '1';
                });
                
                el.addEventListener('click', () => {
                    marker.setPopup(popup);
                    marker.togglePopup();
                });
            });
            
            // Update stats
            document.getElementById('totalCapsules').textContent = data.capsules.length;
            const uniqueCities = new Set(data.capsules.map(c => c.city)).size;
            document.getElementById('countries').textContent = uniqueCities;
        }
    } catch (error) {
        console.error('Error loading capsules:', error);
    }
});

const style = document.createElement('style');
style.textContent = `
    @keyframes pulse-core {
        0%, 100% { box-shadow: 0 0 15px rgba(255, 107, 157, 0.8); }
        50% { box-shadow: 0 0 25px rgba(255, 107, 157, 1); }
    }
    @keyframes ring-pulse {
        0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        50% { transform: translate(-50%, -50%) scale(1.4); opacity: 0.3; }
    }
    .mapboxgl-popup-content {
        background: white;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
        border: 2px solid rgba(255, 107, 157, 0.4);
    }
`;
document.head.appendChild(style);

console.log('Real-time map loaded');
