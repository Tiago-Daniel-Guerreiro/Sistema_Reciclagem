const Constants = {
    STORAGE_KEY: 'markers_manual',

    MARKER_CLASSES: {
        search: 'marker-search',
        manual: 'marker-manual',
        location: 'marker-location',
        pontos_recolha: 'marker-recolha',
    },

    TIPOS: {
        '': 'Todos',
        city: 'Cidade',
        town: 'Vila',
        village: 'Aldeia',
        county: 'Distrito',
        suburb: 'Subúrbio',
        street: 'Rua',
        road: 'Estrada',
        amenity: 'Serviço',
        tourism: 'Turismo',
        building: 'Edifício',
        highway: 'Estrada',
        primary: 'Estrada Principal',
        secondary: 'Estrada Secundária',
        tertiary: 'Estrada Terciária',
        peak: 'Pico',
        water: 'Água',
        natural: 'Natural',
        leisure: 'Lazer',
        other: 'Outros'
    },

    COLORS: {
        origin: {
            fill: '#22c55e',
            stroke: '#16a34a'
        },
        destination: {
            fill: '#ef4444',
            stroke: '#dc2626'
        },
        highlight: {
            fill: '#f0e51f',
            stroke: '#7d7100'
        }
    },

    AREA_STYLE: {
        color: '#e94560',
        weight: 2.5,
        opacity: 0.5,
        fillOpacity: 0.04
    },

    layers: {
        'Mapa Simples': L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>'
        }),
        'Mapa Detalhado': L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }),
        'Mapa de Ruas': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
            attribution: '&copy; Esri'
        }),
        'Mapa de Relevo': L.tileLayer('https://tile.opentopomap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.opentopomap.org/">OpenTopoMap</a>'
        })
    },
};
