const RoutesData = (function () {
    const handler = {
        set(target, property, value) {
            target[property] = value;
            RoutesModule.updateAndDraw();
        }
    };

    // Chama updateAndDraw automaticamente quando uma das variáveis é acedida/modificada
    const data = new Proxy({
        origin: null,
        destination: null
    }, handler);

    function getOrigin() { return data.origin; }
    function getDestination() { return data.destination; }

    function setOriginFromCoords(lat, lng) { 
        data.origin = newDataFromCoords(lat, lng);
    }
    function setDestinationFromCoords(lat, lng) { 
        data.destination = newDataFromCoords(lat, lng);
    }

    function newDataFromCoords(lat, lng) {
        return {
            type: 'coords',
            lat,
            lng,
            nome: 'Localização selecionada',
            id: 'ctx-dest'
        };
    }
    function setOriginFromPonto(pontoId) {
        const ponto = PontosManager.getAllPontos().find(p => p.id === pontoId);
        if (ponto) data.origin = { type: 'ponto', data: ponto };
    }
    function setDestinationFromPonto(pontoId) {
        const ponto = PontosManager.getAllPontos().find(p => p.id === pontoId);
        if (ponto) data.destination = { type: 'ponto', data: ponto };
    }

    function swap() { [data.origin, data.destination] = [data.destination, data.origin]; }

    function clear() {
        data.origin = null;
        data.destination = null;
    }

    function getCoords(point) {
        if (!point) return null;
        if (point.type === 'ponto') return [point.data.lat, point.data.lng];
        if (point.type === 'coords') return [point.lat, point.lng];

        return null;
    }

    function getName(point) {
        if (!point) return null;
        if (point.type === 'ponto') return point.data.nome;
        return point.nome || null;
    }

    return {
        getOrigin,
        getDestination,
        setOriginFromCoords,
        setDestinationFromCoords,
        setOriginFromPonto,
        setDestinationFromPonto,
        swap,
        clear,
        getCoords,
        getName
    };
})();
