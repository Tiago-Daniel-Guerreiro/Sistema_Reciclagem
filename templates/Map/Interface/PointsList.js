const PointsListModule = (function () {
    function init() { }

    function renderPointItem(ponto) {
        const item = Utils.createElement('div', 'points-list-item');
        item.dataset.pontoId = ponto.id;
        item.appendChild(Utils.createElement('strong', '', ponto.nome));

        const actions = Utils.createElement('div', 'points-list-actions');
        actions.appendChild(Utils.createElement('button', 'btn-details', 'Detalhes'));
        actions.appendChild(Utils.createElement('button', 'btn-show', 'Mostrar'));
        actions.appendChild(Utils.createElement('button', 'btn-remove', 'Remover'));
        item.appendChild(actions);

        return item;
    }

    function handlePointsListClick(item, e) {
        if (!item) return;

        const ponto = PontosManager.getAllPontos().find(p => p.id === item.dataset.pontoId);
        if (!ponto) return;

        if (e.target.classList.contains('btn-details')) {
            e.stopPropagation();
            DetalhesModule.abrir(ponto);
            return;
        }

        if (e.target.classList.contains('btn-show')) {
            e.stopPropagation();
            try { document.getElementById('sidebar').hidePopover(); } catch (e) { }
            MapModule.getMap().setView([ponto.lat, ponto.lng], 14);
            return;
        }

        if (e.target.classList.contains('btn-remove')) {
            e.stopPropagation();
            PontosManager.removePonto(item.dataset.pontoId);
            if (ponto.source === 'manual') PontosManager.saveManual();
            renderPointsList();
            return;
        }

        // Click no item = centrar no mapa
        MapModule.getMap().setView([ponto.lat, ponto.lng], 14);
        if (ponto.marker) ponto.marker.openPopup();
    }

    function renderPointsList() {
        const container = document.getElementById('all-points-list');
        if (!container) return;

        const pontosFiltrados = PontosManager.getPontosPorSource('manual');
        container.innerHTML = '';
        const s = pontosFiltrados.length === 1 ? '' : 's'

        container.appendChild(ModalRenderer.renderList(
            pontosFiltrados,
            renderPointItem,
            `${pontosFiltrados.length} Ponto${s} Adicionado${s}`,
        ));

        ModalRenderer.delegateEvents(container, '.points-list-item', handlePointsListClick);
    }

    return {
        init,
        renderPointsList
    };
})();
