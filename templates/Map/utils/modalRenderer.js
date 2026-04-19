const ModalRenderer = (function () {
    function createContainer() { return document.createElement('div'); }

    function createTitle(text) {
        const titulo = document.createElement('h3');
        titulo.className = 'title';
        titulo.textContent = text;
        return titulo;
    }

    function createEmptyState(text) {
        const msg = document.createElement('p');
        msg.className = 'empty';
        msg.textContent = text;
        return msg;
    }

    function buildModal(title, content) {
        const container = createContainer();

        if (title) container.appendChild(createTitle(title));

        if (Array.isArray(content)) content.forEach(el => container.appendChild(el));
        else if (content) container.appendChild(content);

        return container;
    }

    function renderList(items, renderItem, title, emptyText) {
        const container = createContainer();

        if (title) container.appendChild(createTitle(title));
        items.forEach(item => { container.appendChild(renderItem(item)); });

        return container;
    }

    function delegateEvents(container, selector, handler) {
        container.addEventListener('click', (e) => {
            const target = e.target.closest(selector);
            if (target) handler(target, e);
        });
    }

    return {
        createContainer,
        createTitle,
        createEmptyState,
        buildModal,
        renderList,
        delegateEvents
    };
})();
