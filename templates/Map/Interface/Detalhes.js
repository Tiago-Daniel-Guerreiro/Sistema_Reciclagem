const DetalhesModule = (function () {
    let currentData = null;
    let currentEnriched = null;

    function init() {
        ModalManager.criar('detalhes-modal', 'Detalhes', '', [
            { texto: 'Fechar', acao: fechar, className: 'modal-close-btn' }
        ]);
    }

    async function abrir(data) {
        if (!data) return;

        currentData = data;
        const essential = PlaceRenderer.extractEssential(data);

        const botoes = [{ texto: 'Mostrar', acao: mostrar, className: 'modal-show-btn' }];
        if (essential.recolha && !(RecolhaAPI?.isUsingSnapshot?.() || false)) botoes.push({ texto: 'Reportar Problema', acao: reportarProblema, className: 'modal-report-btn' });
        botoes.push({ texto: 'Fechar', acao: fechar, className: 'modal-close-btn' });

        ModalManager.setBotoes('detalhes-modal', botoes);

        ModalManager.setTitulo('detalhes-modal', essential.nome);

        ModalManager.setConteudo('detalhes-modal', Utils.createElement('div', 'det-container', 'Carregando detalhes...'));
        ModalManager.abrir('detalhes-modal');

        try {
            currentEnriched = await ApiService.resolveDetalhes(essential);
            if (currentEnriched?.wikipedia) console.log('[DetalhesModule] Wikipedia encontrada:', currentEnriched.wikipedia?.title);
        } catch (error) {
            console.warn('[DetalhesModule] Erro ao enriquecer detalhes:', error);
            currentEnriched = null;
        }

        ModalManager.setConteudo('detalhes-modal', PlaceRenderer.renderFull(data, currentEnriched));
        if (data.polygon_geojson || data.geojson) MapModule.showArea({ ...data, geojson: data.polygon_geojson || data.geojson });
    }

    function fechar() {
        ModalManager.fechar('detalhes-modal');
        currentData = null;
    }

    function mostrar() {
        if (!currentData) return;
        const essential = PlaceRenderer.extractEssential(currentData);
        try { document.getElementById('sidebar').hidePopover(); } catch (e) { }
        if (Utils.isValidCoord(essential.lat, essential.lng)) MapModule.getMap().setView([essential.lat, essential.lng], 14);
    }

    function reportarProblema() {
        window.open('/reportar/' + currentData.id, '_blank');
    }
    function getDados() { return currentData; }

    return {
        init,
        abrir,
        fechar,
        getDados
    };
})();