// 1. Declare variables globally
window.map = null;
window.marker = null;
window.placesService = null;
window.searchBox = null;
window.geocoder = null;

// 2. The HTML script tag calls this, but we tell it to wait!
window.initMap = function() {
    console.log("Google Maps API loaded successfully. Waiting for modal to open...");
};

// 3. The On-Demand Map Builder
function buildMapNow() {
    // This strict selector guarantees we ignore any old hidden modals!
    const mapDiv = document.querySelector('#form-area #area-map'); 
    
    if (!mapDiv) {
        console.error("CRITICAL: Cannot find the #area-map inside #form-area!");
        return;
    }

    // Ensure the div has explicit height so the map doesn't collapse
    mapDiv.style.height = "350px";
    mapDiv.style.display = "block";

    // If the map already exists, just resize it
    if (window.map) {
        console.log("Resizing existing map...");
        google.maps.event.trigger(window.map, 'resize');
        window.map.setCenter(window.map.getCenter() || { lat: 21.1702, lng: 72.8311 });
        return;
    }

    console.log("Building map for the first time...");
    
    // Initialize Map
    window.map = new google.maps.Map(mapDiv, {
        center: { lat: 21.1702, lng: 72.8311 }, // Default to Surat
        zoom: 12,
        mapTypeId: 'roadmap'
    });

    // Initialize Marker
    window.marker = new google.maps.Marker({
        map: window.map,
        position: { lat: 21.1702, lng: 72.8311 }, // Default to Surat
        draggable: true
    });

    // Initialize Services
    window.placesService = new google.maps.places.PlacesService(window.map);
    window.geocoder = new google.maps.Geocoder();

    // Initialize SearchBox
    const input = document.getElementById("map-search");
    if (input) {
        window.searchBox = new google.maps.places.SearchBox(input);
        window.searchBox.addListener("places_changed", () => {
            const places = window.searchBox.getPlaces();
            if (places.length === 0) return;
            const location = places[0].geometry.location;
            
            window.map.setCenter(location);
            window.map.setZoom(15);
            window.marker.setPosition(location);
            
            document.getElementById('a-lat').value = location.lat();
            document.getElementById('a-lng').value = location.lng();
            
            // Auto-fill the Area Name input box from SearchBox
            document.getElementById('a-name').value = places[0].name;
        });
    }

// Helper function to get the name of the dropped pin via Reverse Geocoding
    function getNeighborhoodName(latLng) {
        window.geocoder.geocode({ location: latLng }, (results, status) => {
            if (status === "OK" && results[0]) {
                
                // 1. ALWAYS update the "Search Location on Map" box with the full address
                const searchInput = document.getElementById('map-search');
                if (searchInput) {
                    searchInput.value = results[0].formatted_address;
                }
                
                // 2. ONLY update the "Area Name" if the user hasn't typed anything yet
                const nameInput = document.getElementById('a-name');
                if (nameInput && nameInput.value.trim() === '') {
                    let areaName = results[0].formatted_address; // Fallback
                    
                    // Hunt for the specific neighborhood name
                    for (let i = 0; i < results.length; i++) {
                        if (results[i].types.includes('sublocality') || results[i].types.includes('locality')) {
                            areaName = results[i].address_components[0].long_name;
                            break;
                        }
                    }
                    nameInput.value = areaName;
                }
            }
        });
    }

    // Map Click Listener
    window.map.addListener('click', (e) => {
        window.marker.setPosition(e.latLng);
        document.getElementById('a-lat').value = e.latLng.lat();
        document.getElementById('a-lng').value = e.latLng.lng();
        
        // Ask Google for the name of where we just clicked
        getNeighborhoodName(e.latLng);
    });
    
    // Marker Drag Listener
    window.marker.addListener('dragend', () => {
        const pos = window.marker.getPosition();
        document.getElementById('a-lat').value = pos.lat();
        document.getElementById('a-lng').value = pos.lng();
        
        // Ask Google for the name of where we just dragged the pin
        getNeighborhoodName(pos);
    });
}

// 4. Attach to Bootstrap's "I am completely finished opening" event
document.addEventListener('DOMContentLoaded', function() {
    const addModalEl = document.getElementById('addModal');
    if (addModalEl) {
        addModalEl.addEventListener('shown.bs.modal', function () {
            // Check if the "New Area" form is the one currently visible
            if (document.getElementById('form-area').style.display !== 'none') {
                buildMapNow();
            }
        });
    }
});

// =========================================================================
// STEP 1 & 2 LOGIC: Handling the Save Area & Discover Shops flow
// =========================================================================

window.handleModalSave = async function() {
    const name = document.getElementById('a-name').value.trim();
    const desc = document.getElementById('a-desc').value.trim();
    const lat = document.getElementById('a-lat').value;
    const lng = document.getElementById('a-lng').value;
    const btn = document.getElementById('modal-save-btn');

    if (!name || !lat || !lng) {
        alert("Please provide an Area Name and select a location on the map.");
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

    try {
        // Create the Area in the backend
        const newArea = await ApiClient.createArea({
            name: name,
            description: desc,
            lat: parseFloat(lat),
            lng: parseFloat(lng)
        });

        // Hide Step 1 (Map/Form) and Show Step 2 (Discovered Shops)
        document.getElementById('area-step-1').style.display = 'none';
        document.getElementById('discovered-shops-container').style.display = 'block';
        document.getElementById('area-saved-msg').textContent = `Area "${newArea.name}" saved!`;
        
        // Hide the main save button since we are done with the form
        btn.style.display = 'none'; 

        // Start hunting for nearby shops!
        // Added 'window.' to fix the ReferenceError, and added fallbacks just in case your API returns nested JSON
        const savedAreaId = newArea.id || newArea.data?.id; 
        window._discoverShops(savedAreaId, { lat: parseFloat(lat), lng: parseFloat(lng) });

        // Update the sidebar list in the background
        if (typeof loadAll === 'function') loadAll();

    } catch (error) {
        console.error("Failed to save area:", error);
        alert(error?.data?.detail || "Failed to save the area.");
        btn.disabled = false;
        btn.textContent = 'Create Area';
    }
};

window._discoverShops = function(areaId, locationParams) {
    const tableBody = document.getElementById('discovered-shops-table');
    
    if (!window.placesService) {
        tableBody.innerHTML = '<tr><td colspan="3" class="text-center py-4 text-danger">Maps service not available.</td></tr>';
        return;
    }

    const request = {
        location: locationParams,
        radius: '1000', // Search within 1km
        type: ['store'] // Look specifically for stores/shops
    };

    window.placesService.nearbySearch(request, (results, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK && results) {
            if (results.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="3" class="text-center py-4 text-muted">No shops found within 1km.</td></tr>';
                return;
            }

            tableBody.innerHTML = ''; // Clear loading spinner

            // Take the top 15 results
            results.slice(0, 15).forEach(place => {
                const row = document.createElement('tr');
                
                const nameCell = document.createElement('td');
                nameCell.className = 'fw-bold';
                nameCell.textContent = place.name;
                
                const addressCell = document.createElement('td');
                addressCell.textContent = place.vicinity;

                const actionCell = document.createElement('td');
                actionCell.className = 'text-end';
                
                const addBtn = document.createElement('button');
                addBtn.className = 'btn btn-sm btn-outline-primary fw-semibold';
                addBtn.textContent = 'Add to CRM';
                addBtn.onclick = () => window.addDiscoveredShop(addBtn, areaId, place.name, place.vicinity);
                
                actionCell.appendChild(addBtn);

                row.appendChild(nameCell);
                row.appendChild(addressCell);
                row.appendChild(actionCell);
                tableBody.appendChild(row);
            });
        } else {
            tableBody.innerHTML = '<tr><td colspan="3" class="text-center py-4 text-danger">Failed to load nearby shops.</td></tr>';
        }
    });
};

window.addDiscoveredShop = async function(btnEl, areaId, shopName, shopAddress) {
    btnEl.disabled = true;
    btnEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    try {
        await ApiClient.createShop({
            name: shopName,
            area_id: areaId,
            address: shopAddress,
            source: 'Google Maps'
        });

        // Turn button green to indicate success
        btnEl.className = 'btn btn-sm btn-success fw-semibold text-white disabled';
        btnEl.innerHTML = '<i class="bi bi-check-lg"></i> Added';
        
        if (typeof loadAll === 'function') loadAll();
    } catch (error) {
        console.error("Error adding shop:", error);
        btnEl.disabled = false;
        btnEl.textContent = 'Retry';
        alert(error?.data?.detail || "Failed to add shop.");
    }
};