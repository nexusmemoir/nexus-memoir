// Map Landing - Real Capsules from API (Fixed hover bug)
mapboxgl.accessToken = 'pk.eyJ1IjoibmV4dXNtZW1vaXIiLCJhIjoiY21rb2sycXN4MDhnMTNjc2FxYWtxaXY1byJ9.PEZQ7jJ02OJZ0ndCVEcc8g';

let map;

function initMap() {
    if (!document.getElementById('mainMap')) {
        console.error('mainMap element not found');
        return;
    }
    
    map = new mapboxgl.Map({
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

    map.on('load', loadCapsules);
}

function createPopupContent(capsule) {
    const icon = capsule.status === 'locked' ? '🔒' : '🎉';
    const statusText = capsule.status === 'locked' ? 'Kilitli' : 'Açıldı';
    const statusColor = capsule.status === 'locked' ? '#f59e0b' : '#10b981';
    
    return `
        <div style="padding: 8px 12px; min-width: 180px;">
            <div style="font-size: 15px; font-weight: 700; color: #0f0f23; margin-bottom: 6px;">${capsule.title}</div>
            <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">📍 ${capsule.city}</div>
            <div style="font-size: 13px; color: #64748b; margin-bottom: 8px;">🎁 ${capsule.unlock_at}</div>
            <div style="font-size: 12px; font-weight: 600; color: white; background: linear-gradient(135deg, #ff6b9d, #ffa94d); padding: 5px 10px; border-radius: 8px; display: inline-block;">${icon} ${statusText}</div>
        </div>
    `;
}

// Fixed: Create marker element with proper structure to avoid position shift on hover
function createMarkerElement() {
    const container = document.createElement('div');
    container.className = 'capsule-marker-container';
    // Fixed dimensions, no transform on container
    container.style.cssText = 'width: 32px; height: 32px; cursor: pointer; position: relative;';
    
    const inner = document.createElement('div');
    inner.className = 'capsule-marker-inner';
    // Inner element handles the visual and animation - transform-origin at center
    inner.style.cssText = `
        width: 16px;
        height: 16px;
        background: linear-gradient(135deg, #ff6b9d, #ffa94d);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        box-shadow: 0 0 15px rgba(255, 107, 157, 0.8);
        transition: all 0.2s ease;
        transform-origin: center center;
    `;
    
    const ring = document.createElement('div');
    ring.className = 'capsule-marker-ring';
    ring.style.cssText = `
        width: 28px;
        height: 28px;
        border: 2px solid rgba(255, 107, 157, 0.4);
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        animation: ring-pulse 2s ease-in-out infinite;
        pointer-events: none;
    `;
    
    container.appendChild(inner);
    container.appendChild(ring);
    
    // Hover effect on inner element only (not container) - prevents position shift
    container.addEventListener('mouseenter', () => {
        inner.style.transform = 'translate(-50%, -50%) scale(1.4)';
        inner.style.boxShadow = '0 0 25px rgba(255, 107, 157, 1)';
    });
    
    container.addEventListener('mouseleave', () => {
        inner.style.transform = 'translate(-50%, -50%) scale(1)';
        inner.style.boxShadow = '0 0 15px rgba(255, 107, 157, 0.8)';
    });
    
    return container;
}

async function loadCapsules() {
    try {
        const response = await fetch('/api/capsules/public');
        const data = await response.json();
        
        if (data.capsules && data.capsules.length > 0) {
            data.capsules.forEach(capsule => {
                const el = createMarkerElement();
                
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
                .setPopup(popup)
                .addTo(map);
                
                el.addEventListener('click', (e) => {
                    e.stopPropagation();
                    marker.togglePopup();
                });
            });
            
            // Update stats
            const totalEl = document.getElementById('totalCapsules');
            const citiesEl = document.getElementById('countries');
            
            if (totalEl) totalEl.textContent = data.capsules.length;
            if (citiesEl) {
                const uniqueCities = new Set(data.capsules.map(c => c.city)).size;
                citiesEl.textContent = uniqueCities;
            }
        } else {
            console.log('No capsules found');
        }
    } catch (error) {
        console.error('Error loading capsules:', error);
    }
}

// Add styles
const style = document.createElement('style');
style.textContent = `
    @keyframes ring-pulse {
        0%, 100% { 
            transform: translate(-50%, -50%) scale(1); 
            opacity: 1; 
        }
        50% { 
            transform: translate(-50%, -50%) scale(1.5); 
            opacity: 0.3; 
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
        font-size: 18px;
        padding: 4px 8px;
        color: #64748b;
    }
    
    .mapboxgl-popup-close-button:hover {
        color: #ff6b9d;
        background: transparent;
    }
    
    /* Ensure markers stay in place */
    .mapboxgl-marker {
        will-change: transform;
    }
    
    .capsule-marker-container {
        will-change: auto;
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMap);
} else {
    initMap();
}

console.log('Map landing initialized');
