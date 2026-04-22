const PointsListModule = (function () {
    function init() { }

    function renderPointItem(ponto) {
        const item = Utils.createElement('div', 'points-list-item');
        item.dataset.pontoId = ponto.id;
        item.appendChild(Utils.createElement('strong', '', ponto.nome));

        const actions = Utils.createElement('div', 'points-list-actions');
        actions.appendChild(Utils.createElement('button', 'btn-details', 'Detalhes'));
        actions.appendChild(Utils.createElement('button', 'btn-show', 'Mostrar'));
        item.appendChild(actions);

        return item;
    }

    function handlePointsListClick(item, e) {
        if (!item) return;

        const ponto = (RecolhaManager?.getPontos?.() || []).find(p => String(p.id) === String(item.dataset.pontoId));
        if (!ponto) return;

        if (e.target.classList.contains('btn-details')) {
            e.stopPropagation();
            DetalhesModule.abrir(ponto);
            return;
        }

        if (e.target.classList.contains('btn-show')) {
            e.stopPropagation();
            // Garante foco mesmo quando estiver em cluster
            RecolhaMarker?.focus?.(ponto, 16);
            return;
        }

        // Click no item = centrar no mapa
        RecolhaMarker?.focus?.(ponto, 16);
    }

    function renderPointsList() {
        const container = document.getElementById('all-points-list');
        if (!container) return;

        const pontosFiltrados = RecolhaManager?.getPontos?.() || [];
        container.innerHTML = '';
        const s = pontosFiltrados.length === 1 ? '' : 's'

        container.appendChild(ModalRenderer.renderList(
            pontosFiltrados,
            renderPointItem,
            `${pontosFiltrados.length} Ponto${s} de Recolha`,
        ));

        ModalRenderer.delegateEvents(container, '.points-list-item', handlePointsListClick);
    }

    return {
        init,
        renderPointsList
    };
})();
