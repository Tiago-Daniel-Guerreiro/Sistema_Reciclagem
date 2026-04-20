const NearbyPointsModule = (function () {
    const MODAL_ID = 'nearby-modal';
    const MAX_POINTS = 6;

    function init() {
        ModalManager.criar(MODAL_ID, '', '', [
            { texto: 'Fechar', acao: fechar, className: 'modal-close-btn' }
        ]);
    }

    function obterPontosProximos(lat, lng) {
        const pontos = RecolhaManager.getPontos() || [];

        // Obter filtros selecionados
        const filtrosSelecionados = new Set([
            ...Array.from(document.querySelectorAll('.residuo-checkbox-eletronico:checked')).map(c => c.dataset.tipo),
            ...Array.from(document.querySelectorAll('.residuo-checkbox-geral:checked')).map(c => c.dataset.tipo)
        ]);

        return pontos.length === 0 ? [] : pontos
            .filter(p => {
                if (ModoBreno.isActive() && !ModoBreno.isPontoEmLisboa_Ponto(p)) return false;
                if (filtrosSelecionados.size === 0) return false;  // Se nenhum filtro, não mostrar

                // Verificar se ponto tem alguma das categorias selecionadas
                if (p.recolha && p.dados_recolha && Array.isArray(p.dados_recolha.categorias)) {
                    return p.dados_recolha.categorias.some(cat => filtrosSelecionados.has(String(cat)));
                }
                return false;
            })
            .map(p => ({ ponto: p, distancia: Utils.calculateDistance(lat, lng, p.lat, p.lng) }))
            .sort((a, b) => a.distancia - b.distancia)
            .slice(0, MAX_POINTS);
    }

    function renderNearbyItem(ponto, distancia) {
        const item = Utils.createElement('div', 'nearby-item');
        item.dataset.pontoId = ponto.id;

        const header = Utils.createElement('div', 'nearby-header');
        header.appendChild(Utils.createElement('strong', '', ponto.nome));
        header.appendChild(Utils.createElement('span', 'nearby-distance', `${distancia.toFixed(1)} km`));
        item.appendChild(header);

        const residuosList = [];
        if (ponto.recolha && ponto.dados_recolha && Array.isArray(ponto.dados_recolha.categorias)) {
            const allCategorias = [
                ...(RecolhaAPI?.getCategoriasGerais() || []),
                ...(RecolhaAPI?.getCategoriasEletronicos() || [])
            ];
            const categMap = new Map(allCategorias.map(c => [Number(c.id), c]));

            ponto.dados_recolha.categorias.forEach(categId => {
                const cat = categMap.get(Number(categId));
                const nome = cat?.nome || String(categId);
                residuosList.push(nome);
            });
        }

        const residuosTexto = residuosList.join(', ');
        item.appendChild(Utils.createElement('small', 'nearby-residuos', residuosTexto));

        const buttons = Utils.createElement('div', 'nearby-buttons');
        buttons.appendChild(Utils.createElement('button', 'btn-details', 'Detalhes'));
        item.appendChild(buttons);

        return item;
    }

    function handleNearbyClick(item, e) {
        if (!item) return;

        // Pegar o ponto de recolha diretamente de RecolhaManager
        const pontoId = item.dataset.pontoId;
        const ponto = (RecolhaManager.getPontos() || []).find(p => String(p.id) === String(pontoId));

        if (!ponto) return;

        if (e.target.classList.contains('btn-details')) {
            fechar();
            // Abrir detalhes do ponto (mesmo método que ao clicar no marker)
            DetalhesModule.abrir(ponto);
        }
    }

    function abrir(lat, lng) {
        const conteudo = ModalRenderer.renderList(
            obterPontosProximos(lat, lng),
            ({ ponto, distancia }) => renderNearbyItem(ponto, distancia),
            'Pontos de Recolha Próximos',
            'Nenhum ponto de recolha encontrado.'
        );

        ModalRenderer.delegateEvents(conteudo, '.nearby-item', handleNearbyClick);
        ModalManager.setConteudo(MODAL_ID, conteudo);
        ModalManager.abrir(MODAL_ID);
    }

    function fechar() { ModalManager.fechar(MODAL_ID); }

    return { init, abrir, fechar };
})();
