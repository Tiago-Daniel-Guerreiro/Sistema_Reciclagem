const PontosStorage = (function () {
    const MANUAL_KEY = Constants.STORAGE_KEY;

    function saveManual(pontosManual) {
        const data = pontosManual.map(p => ({
            id: p.id,
            lat: p.lat,
            lng: p.lng ?? p.lon,
            nome: p.nome,
            source: p.source
        }));

        localStorage.setItem(MANUAL_KEY, JSON.stringify(data));
    }

    function loadManual() {
        try { return JSON.parse(localStorage.getItem(MANUAL_KEY) || '[]'); }
        catch (e) { console.error('Erro ao carregar pontos manuais de localStorage:', e); }
        return [];
    }

    function clear() { localStorage.removeItem(MANUAL_KEY); }

    return {
        saveManual,
        loadManual,
        clear
    };
})();
