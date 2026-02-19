const pontos = [
{ lat: 38.7167, lng: -9.1333, nome: 'Lisboa' },
{ lat: 41.1579, lng: -8.6291, nome: 'Porto' },
{ lat: 39.6519, lng: -7.2361, nome: 'Covilhã' },
{ lat: 40.5364, lng: -7.2711, nome: 'Guarda' },
{ lat: 37.1412, lng: -7.6701, nome: 'Sagres' }
];

function adicionarPontos() {
    pontos.forEach(function(ponto) {
    L.marker([ponto.lat, ponto.lng]).addTo(map)
        .bindPopup(ponto.nome);
    });
}