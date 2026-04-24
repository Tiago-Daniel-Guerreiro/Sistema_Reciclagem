const ModalManager = (function () {
    const modaisCarregados = {};

    function criar(id, titulo, conteudo, botoes = []) {
        let overlay = document.getElementById(`${id}-overlay`);

        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = `${id}-overlay`;
            overlay.className = 'modal-overlay';

            overlay.innerHTML = `
                <div class="modal" id="${id}-modal">
                    <button class="modal-close" data-modal-close="${id}">X</button>
                    <div class="modal-header"><h2>${titulo}</h2></div>
                    <div class="modal-body" id="${id}-body"></div>
                    <div class="modal-footer" id="${id}-footer"></div>
                </div>
            `;

            document.body.appendChild(overlay);
            modaisCarregados[id] = overlay;

            overlay.addEventListener('click', (e) => { if (e.target === overlay) fechar(id); });
            overlay.querySelector('[data-modal-close]').addEventListener('click', () => fechar(id));
        }

        // Preencher conteúdo
        if (conteudo) {
            const body = document.getElementById(`${id}-body`);

            if (typeof conteudo === 'string') body.innerHTML = conteudo
            else {
                body.innerHTML = '';
                body.appendChild(conteudo);
            }
        }

        // Adicionar botões
        const footer = document.getElementById(`${id}-footer`);

        if (botoes.length > 0) {
            footer.innerHTML = '';
            botoes.forEach(btn => {
                const button = document.createElement('button');
                button.className = btn.className || 'action-btn';
                button.textContent = btn.texto;
                button.addEventListener('click', btn.acao);
                footer.appendChild(button);
            });
        }
        return modaisCarregados[id];
    }

    function abrir(id) {
        const modal = modaisCarregados[id] || document.getElementById(`${id}-overlay`);
        if (modal) {
            modal.style.display = 'flex';
            try { document.getElementById('sidebar').hidePopover(); } catch (e) { }
        }
    }

    function fechar(id) {
        const modal = modaisCarregados[id] || document.getElementById(`${id}-overlay`);
        if (modal) modal.style.display = 'none';
    }

    function setConteudo(id, conteudo) {
        const body = document.getElementById(`${id}-body`);
        const header = document.getElementById(`${id}-modal`).querySelector('.modal-header h2');
        if (!body) return;
        if (typeof conteudo === 'string') body.innerHTML = conteudo;
        else {
            body.innerHTML = '';
            body.appendChild(conteudo);
        }

        // Mover title do body para o header se existir
        const title = body.querySelector('.title');
        if (title && header) {
            header.textContent = title.textContent;
            title.remove();
        }
    }

    function setBotoes(id, botoes) {
        const footer = document.getElementById(`${id}-footer`);

        if (!footer) return;

        footer.innerHTML = '';
        botoes.forEach(btn => {
            const button = document.createElement('button');
            button.className = btn.className || 'action-btn';
            button.textContent = btn.texto;
            button.addEventListener('click', btn.acao);
            footer.appendChild(button);
        });
    }

    function existe(id) { return Boolean(modaisCarregados[id]) || Boolean(document.getElementById(`${id}-overlay`)); }

    function setTitulo(id, titulo) {
        const modal = document.getElementById(`${id}-modal`);
        if (!modal) return;

        const h2 = modal.querySelector('.modal-header h2');
        if (h2) h2.textContent = titulo;
    }

    return {
        criar,
        abrir,
        fechar,
        setConteudo,
        setBotoes,
        setTitulo,
        existe
    };
})();
