const PlaceRenderer = {
    extractEssential(raw = {}) {
        const lat = parseFloat(raw.lat);
        const lng = parseFloat(Format.firstValid([raw.lng, raw.lon, raw.longitude]));
        const recolha = raw.recolha === true;

        const categorias = recolha && Array.isArray(raw.dados_recolha?.categorias) ? raw.dados_recolha.categorias : [];

        return {
            id: Format.firstValid([raw.id, raw.place_id, raw.osm_id]),
            nome: Format.firstValid([raw.nome, raw.name, raw.display_name, raw.displayName, 'Local']),
            lat: lat,
            lng: lng,
            recolha,
            dados_recolha: recolha ? { categorias } : null
        };
    },

    _determineTipoRecolha(categorias) {
        if (!Array.isArray(categorias) || categorias.length === 0) return 'Ponto de Recolha';

        const categoriasGerais = RecolhaAPI?.getCategoriasGerais() || [];
        const categoriasEletronicos = RecolhaAPI?.getCategoriasEletronicos() || [];

        const generalIds = new Set(categoriasGerais.map(c => Number(c.id)));
        const eletronicosIds = new Set(categoriasEletronicos.map(c => Number(c.id)));

        let temGeral = false;
        let temEletronico = false;

        categorias.forEach(catId => {
            const numId = Number(catId);
            if (generalIds.has(numId)) temGeral = true;
            if (eletronicosIds.has(numId)) temEletronico = true;
        });

        if (temGeral && temEletronico) return 'Ponto de Recolha - Eletrônicos e Geral';
        if (temEletronico) return 'Ponto de Recolha - Eletrônicos';
        if (temGeral) return 'Ponto de Recolha - Geral';

        return 'Ponto de Recolha';
    },


    renderFull(raw, enriched = null) {
        const essential = this.extractEssential(raw);
        const container = document.createElement('div');

        if (!Utils.isValidCoord(essential.lat, essential.lng)) {
            container.innerHTML = '<p>Coordenadas inválidas</p>';
            return container;
        }

        container.className = 'det-container';

        let html = '';

        if (enriched?.wikipedia?.extract) {
            html += `<div class="det-section">
    <div class="det-label-title">Descrição</div>
    <div class="det-description">${Utils.escapeHtml(enriched.wikipedia.extract.substring(0, 400)).replace(/\n/g, '<br>')}</div>
</div>`;
        }

        if (essential.recolha && essential.dados_recolha?.categorias.length > 0) {
            const allCategorias = [
                ...(RecolhaAPI?.getCategoriasGerais() || []),
                ...(RecolhaAPI?.getCategoriasEletronicos() || [])
            ];
            const categMap = new Map(allCategorias.map(c => [Number(c.id), c]));

            const tags = essential.dados_recolha.categorias
                .map(categId => {
                    const cat = categMap.get(Number(categId));
                    const nome = cat?.nome || String(categId);
                    return `<span class="det-tag">${Utils.escapeHtml(nome)}</span>`;
                })
                .join('');
            html += `<div class="det-section">
    <div class="det-label-title">Tipos de Resíduos Aceites</div>
    <div class="det-tags">${tags}</div>
</div>`;
        }

        // Mostrar coordenadas
        html += `<div class="det-section">
    <div class="det-label-title">Localização</div>
    <div class="det-value det-coords">
        <span style="display: block; font-size: 0.9em; margin: 4px 0;">
            <strong>Latitude:</strong> ${essential.lat.toFixed(6)}
        </span>
        <span style="display: block; font-size: 0.9em; margin: 4px 0;">
            <strong>Longitude:</strong> ${essential.lng.toFixed(6)}
        </span>
    </div>
</div>`;

        // Links externos
        html += `<div class="det-section det-links">
    <a class="det-ext-btn" href="https://www.google.com/maps?q=${essential.lat},${essential.lng}" target="_blank" rel="noopener">Google Maps</a>
    <a class="det-ext-btn" href="https://www.openstreetmap.org/?mlat=${essential.lat}&mlon=${essential.lng}&zoom=15" target="_blank" rel="noopener">OpenStreetMap</a>`;

        if (enriched?.wikipedia?.url) html += `<a class="det-ext-btn" href="${enriched.wikipedia.url}" target="_blank" rel="noopener">Wikipedia</a>`;

        html += `</div>`;

        container.innerHTML = html;

        return container;
    }
};
