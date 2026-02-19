
function pesquisarArea(nome) {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(nome)}&format=json&polygon_geojson=1`;
    
    console.log('Pesquisando:', url);
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            mostrarResultados(data);
        })
        .catch(error => {
            console.error('Erro na pesquisa:', error);
            document.getElementById('results').innerHTML = '<div style="color: red; padding: 15px;">Erro ao pesquisar</div>';
        });
}

function mostrarResultados(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    if (data.length === 0) {
        resultsDiv.innerHTML = '<div style="color: orange; padding: 15px;">Nenhum resultado encontrado</div>';
        return;
    }

    data.forEach((resultado) => {
        const item = document.createElement('div');
        item.className = 'result-item';
        const tipo = resultado.address_type || resultado.type || resultado.category || 'Local';
        item.innerHTML = `
            <div class="result-name">${resultado.name}</div>
            <div class="result-type">${tipo}</div>
        `;
        item.onclick = () => marcarArea(resultado);
        resultsDiv.appendChild(item);
    });
}

function marcarArea(resultado) {
    if (geoJsonLayer) {
        map.removeLayer(geoJsonLayer);
    }

    if (resultado.geojson) {
        geoJsonLayer = L.geoJSON(resultado.geojson, {
            style: {
                color: '#ff00e6ff',
                weight: 2.5,
                opacity: 0.5,
                fillOpacity: 0.03
            }
        }).addTo(map);

        const bounds = geoJsonLayer.getBounds();
        map.fitBounds(bounds);
    } else {
        const lat = parseFloat(resultado.lat);
        const lng = parseFloat(resultado.lon);
        
        L.marker([lat, lng]).addTo(map)
            .bindPopup(resultado.name)
            .openPopup();
        
        map.setView([lat, lng], 12);
    }
}

function search(searchTerm) {
    if (searchTerm) {
        pesquisarArea(searchTerm);
    }
}

function search_init() {
    // Pesquisar
    document.getElementById('search-submit-btn').addEventListener('click', function() {
        search(document.getElementById('search-input').value.trim());
    });

    // Pesquisar com Enter
    document.getElementById('search-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            search(this.value.trim());
        }
    });
}

function locate_me_init() {
    document.getElementById('locate-me-btn').addEventListener('click', function() {
        if (navigator.geolocation) {
            this.textContent = 'Localizando...';
            this.disabled = true;
            
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    map.setView([lat, lng], 13);
                    L.marker([lat, lng]).addTo(map)
                        .bindPopup('Sua localização')
                        .openPopup();
                    
                    document.getElementById('locate-me-btn').textContent = 'Localizar-me';
                    document.getElementById('locate-me-btn').disabled = false;
                },
                function(error) {
                    alert('Erro ao obter localização: ' + error.message);
                    document.getElementById('locate-me-btn').textContent = 'Localizar-me';
                    document.getElementById('locate-me-btn').disabled = false;
                }
            );
        } else {
            alert('Geolocalização não é suportada pelo seu navegador');
        }
    });
}

function sidebar_init() {
    search_init();
    locate_me_init();
}