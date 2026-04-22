(async function () {
    const MODULES = [
        SidebarModule,
        SearchModule,
        PointsListModule,
        ModalManager,
        DetalhesModule,
        NearbyPointsModule,
        RoutesModule,
        ContextMenuModule
    ];

    const ESSENTIAL_MODULES = [MapModule, PontosManager, ModoBreno];

    function _safeInit(module) {
        try { if (typeof module?.init === 'function') module.init(); }
        catch (e) { console.error(`Erro ao inicializar: ${module}:`, e); }
    }

    async function _initModulesInBatches(modules, batchSize = 2) {
        for (let i = 0; i < modules.length; i += batchSize) {
            await new Promise(resolve => requestAnimationFrame(resolve));
            modules.slice(i, i + batchSize).forEach(_safeInit);
        }
    }

    ESSENTIAL_MODULES.forEach(_safeInit);

    // Sync Recolha em background
    (async () => {
        try { await RecolhaManager.init(MapModule.getMarkersLayerGroup()); }
        catch (e) { console.error('Erro ao inicializar recolha:', e); }

        // Atualizar lista de pontos (separador "Pontos")
        try { PointsListModule?.renderPointsList?.(); } catch (e) { /* noop */ }

        // Permite focar um ponto pelo link: /map/?focus=<id>
        try {
            const params = new URLSearchParams(window.location.search || '');
            const focusId = params.get('focus');
            if (focusId) {
                const pontos = RecolhaManager.getPontos?.() || [];
                const ponto = pontos.find(p => String(p.id) === String(focusId));
                if (ponto) {
                    RecolhaMarker?.focus?.(ponto, 16);
                }
            }
        } catch (e) {
            console.warn('[app] Falha ao aplicar focus:', e);
        }
    })();

    requestIdleCallback(() => { _initModulesInBatches(MODULES); }, { timeout: 350 });
})();
