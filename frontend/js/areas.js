let areas = [];
let map;
let marker;
let placesService;
let currentAreaId = null;

async function initMap() {
    const defaultLoc = { lat: 18.5204, lng: 73.8567 }; // Default to Pune
    map = new google.maps.Map(document.getElementById("area-map"), {
        center: defaultLoc,
        zoom: 12,
    });

    marker = new google.maps.Marker({
        map: map,
        position: defaultLoc,
        draggable: true
    });

    placesService = new google.maps.places.PlacesService(map);

    // Search Box integration
    const input = document.getElementById("map-search");
    const searchBox = new google.maps.places.SearchBox(input);

    map.controls[google.maps.ControlPosition.TOP_LEFT].push(input);

    map.addListener("bounds_changed", () => {
        searchBox.setBounds(map.getBounds());
    });

    searchBox.addListener("places_changed", () => {
        const places = searchBox.getPlaces();
        if (places.length == 0) return;

        const place = places[0];
        if (!place.geometry || !place.geometry.location) return;

        if (place.geometry.viewport) {
            map.fitBounds(place.geometry.viewport);
        } else {
            map.setCenter(place.geometry.location);
            map.setZoom(15);
        }

        marker.setPosition(place.geometry.location);
        updateLatLng(place.geometry.location);

        // Auto-fill area name if empty
        if (!document.getElementById('a-name').value) {
            document.getElementById('a-name').value = place.name;
        }
    });

    // Allow dragging marker
    marker.addListener('dragend', () => {
        updateLatLng(marker.getPosition());
    });

    // Click on map to move marker
    map.addListener('click', (e) => {
        marker.setPosition(e.latLng);
        updateLatLng(e.latLng);
    });
}

function updateLatLng(location) {
    document.getElementById('a-lat').value = location.lat();
    document.getElementById('a-lng').value = location.lng();
}

async function loadAreas() {
    areas = await apiGet('/areas/');
    document.getElementById('area-count').textContent = `${areas.length} areas`;
    document.getElementById('areas-table').innerHTML = areas.length
        ? areas.map((a, i) => `<tr><td>${a.id}</td><td class="fw-semibold">${a.name}</td><td class="text-muted">${a.city || '—'}</td><td>${a.shops_count ?? '—'}</td></tr>`).join('')
        : '<tr><td colspan="4" class="text-center py-4 text-muted">No areas yet.</td></tr>';
    document.getElementById('s-area').innerHTML = '<option value="">-- Select Area --</option>' +
        areas.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
}

async function loadShops() {
    const shops = await apiGet('/shops/?limit=200');
    document.getElementById('shops-table').innerHTML = shops.length
        ? shops.map(s => `
        <tr>
            <td class="fw-semibold">${s.name}</td>
            <td>${s.area_name || 'Area #' + s.area_id}</td>
            <td class="text-muted small">${s.address || '—'}</td>
            <td>${s.phone || '—'}</td>
            <td><span class="badge bg-success">Active</span></td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteShop(${s.id})" title="Delete Shop"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('')
        : '<tr><td colspan="6" class="text-center py-4 text-muted">No shops yet.</td></tr>';
}

// Reset modal when reopened
document.getElementById('addAreaModal').addEventListener('show.bs.modal', function () {
    document.getElementById('step-1-area').style.display = 'block';
    document.getElementById('step-2-shops').style.display = 'none';
    document.getElementById('a-name').value = '';
    document.getElementById('a-lat').value = '';
    document.getElementById('a-lng').value = '';
    document.getElementById('map-search').value = '';
    setTimeout(() => {
        if (!map) initMap();
        else google.maps.event.trigger(map, 'resize');
    }, 200);
});

// Step 1: Save Area
document.getElementById('save-area-btn').addEventListener('click', async () => {
    const name = document.getElementById('a-name').value;
    const lat = document.getElementById('a-lat').value;
    const lng = document.getElementById('a-lng').value;

    if (!name) return showToast("Area Name is required", "error");

    const btn = document.getElementById('save-area-btn');
    btn.disabled = true;
    try {
        const payload = {
            name: name,
            lat: lat ? parseFloat(lat) : null,
            lng: lng ? parseFloat(lng) : null
        };
        const newArea = await apiPost('/areas/', payload);
        currentAreaId = newArea.id;

        showToast('Area created!');
        loadAreas();

        // Transition to Step 2
        document.getElementById('step-1-area').style.display = 'none';
        document.getElementById('step-2-shops').style.display = 'block';

        if (lat && lng) {
            discoverShops(parseFloat(lat), parseFloat(lng));
        } else {
            document.getElementById('discovered-shops-table').innerHTML = '<tr><td colspan="3" class="text-muted text-center py-3">No coordinates saved to discover shops.</td></tr>';
        }

    } catch (e) { showToast(e.message, 'error'); }
    finally { btn.disabled = false; }
});

// Step 2: Discover Shops
function discoverShops(lat, lng) {
    document.getElementById('discovered-shops-table').innerHTML = '<tr><td colspan="3" class="text-muted text-center py-3"><div class="spinner-border spinner-border-sm me-2"></div>Searching nearby shops...</td></tr>';

    const location = new google.maps.LatLng(lat, lng);
    const request = {
        location: location,
        radius: '1000', // 1km radius
        type: ['store']
    };

    placesService.nearbySearch(request, (results, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK && results.length > 0) {
            // Filter out exact matches that might just be the city center, prioritize actual stores
            const shopsHtml = results.slice(0, 15).map(place => {
                const address = place.vicinity || '';
                return `
                <tr>
                    <td class="fw-semibold">${place.name}</td>
                    <td class="small text-muted">${address}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-success add-discovered-shop-btn" 
                                onclick="addDiscoveredShop(this, '${escapeHtml(place.name)}', '${escapeHtml(address)}')">
                            <i class="bi bi-plus-lg me-1"></i>Add
                        </button>
                    </td>
                </tr>
                `;
            }).join('');
            document.getElementById('discovered-shops-table').innerHTML = shopsHtml;
        } else {
            document.getElementById('discovered-shops-table').innerHTML = '<tr><td colspan="3" class="text-muted text-center py-3">No shops found automatically in this radius.</td></tr>';
        }
    });
}

// Add Discovered Shop to CRM
window.addDiscoveredShop = async (btn, name, address) => {
    btn.disabled = true;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    try {
        await apiPost('/shops/', {
            name: name,
            area_id: currentAreaId,
            address: address,
            source: 'Google Maps'
        });
        btn.classList.remove('btn-outline-success');
        btn.classList.add('btn-success');
        btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Added';
        loadShops();
        loadAreas(); // Update count
    } catch (e) {
        showToast(e.message, 'error');
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
};

// Helper to escape HTML quotes for the onclick handler
function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

document.getElementById('save-shop-btn').addEventListener('click', async () => {
    const areaId = document.getElementById('s-area').value;
    if (!areaId) return showToast('Select an area', 'error');
    const btn = document.getElementById('save-shop-btn');
    btn.disabled = true;
    try {
        await apiPost('/shops/', { name: document.getElementById('s-name').value, area_id: parseInt(areaId), address: document.getElementById('s-addr').value, phone: document.getElementById('s-phone').value });
        bootstrap.Modal.getInstance(document.getElementById('addShopModal')).hide();
        showToast('Shop added!');
        loadShops();
        loadAreas();
    } catch (e) { showToast(e.message, 'error'); }
    finally { btn.disabled = false; }
});

window.deleteShop = async (id) => {
    if (!confirm('Are you sure you want to delete this shop?')) return;
    try {
        await apiDelete('/shops/' + id);
        showToast('Shop deleted successfully', 'success');
        loadShops();
        loadAreas();
    } catch (e) {
        showToast(e.message || 'Failed to delete shop', 'error');
    }
};

loadAreas();
loadShops();
