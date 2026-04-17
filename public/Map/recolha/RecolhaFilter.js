const RecolhaFilter = (function () {
    let _timeout = null;

    function _renderCheckbox(cat, className, checked) {
        const input = Utils.createElement('input', '', '');

        input.type = 'checkbox';
        input.className = className;
        input.dataset.tipo = cat.id;
        input.checked = checked;
        input.addEventListener('change', aplicarFiltros);

        const label = Utils.createElement('label', 'filter-item', '');
        label.appendChild(input);
        const text = Utils.createElement('span', '', `${cat.nome || cat.id} `);
        if (cat.pontos && cat.pontos > 0) {
            const count = Utils.createElement('small', '', `(${cat.pontos})`);
            text.appendChild(count);
        }
        label.appendChild(text);
        return label;
    }

    function _renderToggleCheckbox(container, className, titleElement) {
        if (!titleElement) return;

        // Remover checkbox antigo se existir
        const existingCheckbox = titleElement.querySelector('.residuo-toggle-checkbox');
        if (existingCheckbox) existingCheckbox.remove();

        // Criar checkbox
        const checkbox = Utils.createElement('input', '', '');
        checkbox.type = 'checkbox';
        checkbox.className = 'residuo-toggle-checkbox';
        checkbox.title = 'Ativar/Desativar tudo';

        checkbox.addEventListener('change', () => {
            const checkboxes = container.querySelectorAll(`.${className}`);
            checkboxes.forEach(cb => {
                cb.checked = checkbox.checked;
                cb.dispatchEvent(new Event('change'));
            });
        });

        // Clicar no título também aciona o checkbox
        titleElement.style.cursor = 'pointer';
        titleElement.addEventListener('click', (e) => {
            // Não acionar se clicar no checkbox diretamente
            if (e.target === checkbox) return;
            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event('change'));
        });

        // Inserir checkbox no início do title (à esquerda)
        titleElement.insertBefore(checkbox, titleElement.firstChild);

        // Atualizar estado do toggle
        setTimeout(() => {
            const checkboxes = container.querySelectorAll(`.${className}`);
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            const someChecked = Array.from(checkboxes).some(cb => cb.checked);
            checkbox.checked = allChecked;
            checkbox.indeterminate = someChecked && !allChecked;
        }, 50);
    }

    function _renderTab(container, categorias, className, checked = false) {
        if (!container) return;
        container.innerHTML = '';
        if (!categorias?.length) return;

        categorias
            .slice()
            .forEach(cat => {
                const checkbox = _renderCheckbox(cat, className, checked);
                if (checkbox) container.appendChild(checkbox);
            });
    }

    async function render() {
        const eleContainer = document.getElementById('residuos-filters-eletronicos');
        const geraiContainer = document.getElementById('residuos-filters-gerais');

        if (!eleContainer || !geraiContainer) return;

        // Encontrar os títulos
        const parent = eleContainer.parentElement;
        const eleTitle = parent?.querySelector('h4.residuo-category-title');
        const geraiTitle = parent?.querySelectorAll('h4.residuo-category-title')[1];

        const catEle = RecolhaAPI.getCategoriasEletronicos() || [];
        const catGerais = RecolhaAPI.getCategoriasGerais() || [];

        // Renderizar abas
        _renderTab(
            eleContainer,
            catEle,
            'residuo-checkbox-eletronico',
            true
        );
        _renderTab(
            geraiContainer,
            catGerais,
            'residuo-checkbox-geral',
            false
        );

        // Renderizar checkboxes de toggle
        if (eleTitle) _renderToggleCheckbox(eleContainer, 'residuo-checkbox-eletronico', eleTitle);
        if (geraiTitle) _renderToggleCheckbox(geraiContainer, 'residuo-checkbox-geral', geraiTitle);

        await aplicarFiltros();
    }

    function aplicarFiltros() {
        return new Promise(resolve => {
            clearTimeout(_timeout);
            _timeout = setTimeout(async () => {
                const checked = new Set([
                    ...Array.from(document.querySelectorAll('.residuo-checkbox-eletronico:checked')).map(c => c.dataset.tipo),
                    ...Array.from(document.querySelectorAll('.residuo-checkbox-geral:checked')).map(c => c.dataset.tipo)
                ]);

                if (checked.size === 0) {
                    RecolhaMarker.limpar();
                    resolve();
                    return;
                }

                // Passa todos os pontos - renderMarkersEmChunks divide automaticamente em batches
                const pontos = RecolhaAPI.getPontos() || [];

                await RecolhaMarker.aplicarFiltros(pontos, checked);
                resolve();
            }, 150);
        });
    }

    return {
        render,
        aplicarFiltros
    };
})();
