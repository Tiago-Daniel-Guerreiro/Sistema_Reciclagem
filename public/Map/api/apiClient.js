const ApiClient = (function () {
    const BASE_URL = 'https://nominatim.openstreetmap.org';

    function searchNominatim(query, options = {}) {
        const params = new URLSearchParams({
            format: 'json',
            polygon_geojson: '1',
            addressdetails: '1',
            namedetails: '1',
            extratags: '1',
            countrycodes: 'pt',
            limit: options.limit || '15',
            'accept-language': 'pt',
            viewbox: getSearchViewbox(),
            bounded: '1',
            q: query
        });

        return fetch(`${BASE_URL}/search?${params.toString()}`)
            .then(r => r.json())
            .then(data => {
                let results = Format.normalizeArray(data, () => { return data.map(item => normalizeNominatimResult(item)); });

                if (options.type && options.type.trim()) {
                    const typeFilter = Format.normalize(options.type);
                    results = typeFilter === 'other' ? filterotherType(results) : filterSpecificType(results, typeFilter);
                }
                return results;
            })
            .catch(err => {
                console.error('Erro Nominatim:', err);
                return [];
            });
    }

    function filterotherType(items) {
        return items.filter(item => {
            return !Object.keys(Utils.getTiposPesquisa()).includes(Format.normalize(item.addresstype))
                && !Object.keys(Utils.getTiposPesquisa()).includes(Format.normalize(item.category));
        });
    }

    function filterSpecificType(items, typeFilter) {
        return items.filter(item => {
            return Format.normalize(item.addresstype) === typeFilter
                || Format.normalize(item.category) === typeFilter;
        });
    }

    function getSearchViewbox() {
        if (ModoBreno.isActive()) return ModoBreno.getSearchViewbox_Lisboa();

        // Fallback se MapModule não inicializado
        const bounds = MapModule.getPortugalContinentalBounds?.() || [[36.960, -9.500], [42.154, -6.189]];
        return `${bounds[0][1]},${bounds[0][0]},${bounds[1][1]},${bounds[1][0]}`;
    }

    function reverseGeocode(lat, lng) {
        const params = new URLSearchParams({
            format: 'jsonv2',
            lat,
            lon: lng,
            addressdetails: '1',
            namedetails: '1',
            zoom: '18',
            'accept-language': 'pt'
        });

        return fetch(`${BASE_URL}/reverse?${params.toString()}`)
            .then(r => r.json())
            .then(data => {
                if (data?.error) return null;
                return normalizeNominatimResult(data);
            })
            .catch(err => {
                console.error('Erro reverse:', err);
                return null;
            });
    }

    function normalizeNominatimResult(item) {
        const addressType = Format.defaultIfEmpty(item.addresstype, 'place');
        const display_name = Format.defaultIfEmpty(item.display_name);

        // Determinar tipo com lógica de class especial
        let typeForLookup;
        if (item.class === 'place') typeForLookup = Format.firstValid([item.type, item.addresstype, 'other']);
        else if (item.class === 'boundary') typeForLookup = Format.firstValid([item.addresstype, item.type, 'other']);
        else typeForLookup = Format.firstValid([item.class, item.type, item.addresstype, 'other']);

        return {
            lat: parseFloat(item.lat),
            lng: parseFloat(item.lon),
            name: Format.firstValid([item.namedetails?.['name:pt'], item.namedetails?.name, display_name?.split(',')[0], 'Sem nome']),
            display_name: display_name,
            type: item.type || '',
            class: item.class || '',
            addresstype: addressType,
            osm_type: Format.defaultIfEmpty(item.osm_type, ''),
            osm_id: Format.defaultIfEmpty(item.osm_id, item.id),
            tipo_traduzido: Constants.TIPOS[typeForLookup] || 'Outro',
            category: Format.defaultIfEmpty(item.category),
            polygon_geojson: Format.defaultIfEmpty(item.geojson),
            boundingbox: Format.defaultIfEmpty(item.boundingbox),
            extratags: item.extratags || {}
        };
    }

    function fetchRouteOSRM(fromLat, fromLng, toLat, toLng) {
        return fetch(`https://router.project-osrm.org/route/v1/driving/${fromLng},${fromLat};${toLng},${toLat}?overview=full&geometries=geojson&steps=true`)
            .then(r => r.json())
            .then(data => {
                if (data.code !== 'Ok') {
                    console.warn('OSRM:', data);
                    return null;
                }
                const route = data.routes[0];

                return {
                    coordinates: route.geometry.coordinates.map(c => [c[1], c[0]]),
                    distance: Utils.formatDistance(route.distance),
                    legs: route.legs
                };
            })
            .catch(err => {
                console.error('Erro OSRM:', err);
                return null;
            });
    }

    return {
        searchNominatim,
        reverseGeocode,
        fetchRouteOSRM
    };
})();
