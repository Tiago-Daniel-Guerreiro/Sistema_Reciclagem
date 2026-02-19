var map = L.map('map').setView([39.5, -8.0], 6);
var geoJsonLayer = null;

const Layers = {
    definitions: {
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

    initialize: function () {
        this.definitions['Mapa Simples'].addTo(window.map);
        window.map.setMinZoom(7);
        L.control.layers(this.definitions).addTo(window.map);
    }
};