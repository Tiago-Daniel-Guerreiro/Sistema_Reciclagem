const RecolhaManager = (function () {
    let _initialized = false;

    async function init(markersLayer) {
        if (_initialized) return;
        _initialized = true;

        try {
            // Inicializa os cluster antes de tudo
            RecolhaMarker.init(markersLayer);

            // Mostrar loading durante sync
            MapModule.setLoading(true);
            await RecolhaAPI.sync();
            MapModule.setLoading(false);

            await RecolhaFilter.render();
        } catch (e) {
            console.error('Erro ao inicializar RecolhaManager:', e);
            MapModule.setLoading(false);
            _initialized = false;
        }
    }

    return {
        init,
        getClusterGroup: () => RecolhaMarker.getClusterGroup(),
        getCategorias: () => RecolhaAPI.getCategorias(),
        getCategoriasGerais: () => RecolhaAPI.getCategoriasGerais(),
        getCategoriasEletronicos: () => RecolhaAPI.getCategoriasEletronicos(),
        getPontos: () => RecolhaAPI.getPontos()
    };
})();
