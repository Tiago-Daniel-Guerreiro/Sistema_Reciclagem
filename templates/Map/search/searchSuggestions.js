const SearchSuggestions = (function () {
    let suggestionsContainer = null;
    let suggestionsList = null;
    let currentSuggestions = [];
    let currentIndex = -1;
    let debounceTimer = null;
    const DEBOUNCE_TIME = 300;
    const MIN_CHARS = 2;

    function init() {
        suggestionsContainer = document.getElementById('suggestions-container');
        suggestionsList = document.getElementById('suggestions-list');
    }

    function show() { suggestionsContainer?.classList.remove('hidden'); }

    function hide() {
        suggestionsContainer?.classList.add('hidden');
        currentSuggestions = [];
        currentIndex = -1;
    }

    function fetchWithDebounce(query, typeFilter) {
        if (debounceTimer) clearTimeout(debounceTimer);

        if (query.length < MIN_CHARS) {
            hide();
            return;
        }

        debounceTimer = setTimeout(() => {
            ApiClient.searchNominatim(query, { type: typeFilter, limit: 8 })
                .then(data => {
                    currentSuggestions = data.slice(0, 8);
                    currentIndex = -1;
                    render(currentSuggestions);
                })
                .catch(err => {
                    console.error('Erro ao buscar sugestões:', err);
                    hide();
                });
        }, DEBOUNCE_TIME);
    }

    function render(suggestions) {
        suggestionsList.innerHTML = '';

        if (suggestions.length === 0) {
            hide();
            return;
        }

        suggestions.forEach((suggestion, index) => {
            const li = document.createElement('li');
            li.className = 'suggestion-item';
            li.dataset.index = index;

            li.appendChild(Utils.createElement('span', 'suggestion-icon'));
            li.appendChild(Utils.createElement('span', 'suggestion-text', Utils.escapeHtml(suggestion.name)));

            // Mostrar tipo se disponível
            const tipoText = suggestion.tipo_traduzido || '';
            if (tipoText) li.appendChild(Utils.createElement('span', 'type-badge', Utils.escapeHtml(tipoText)));

            li.addEventListener('click', () => selectSuggestion(suggestion));
            li.addEventListener('mouseenter', () => {
                currentIndex = index;
                updateActiveStyle();
            });

            suggestionsList.appendChild(li);
        });

        show();
    }

    function selectSuggestion(suggestion) {
        const input = document.getElementById('search-input');
        if (input) input.value = suggestion.name;
        hide();
        document.getElementById('search-submit-btn')?.click();
    }

    function selectNext() {
        if (currentIndex >= currentSuggestions.length - 1) return

        currentIndex++;
        updateActiveStyle();
        scrollToActive();
    }

    function selectPrevious() {
        if (currentIndex > 0) {
            currentIndex--;
            updateActiveStyle();
            scrollToActive();
        }

        if (currentIndex === 0) {
            currentIndex = -1;
            updateActiveStyle();
        }
    }

    function handleKeyDown(e, callback) {
        const suggestionsVisible = !suggestionsContainer?.classList.contains('hidden') && currentSuggestions.length > 0;
        if (!suggestionsVisible) return;
        if (['ArrowDown', 'ArrowUp', 'Escape'].includes(e.key)) { e.preventDefault(); }

        switch (e.key) {
            case 'ArrowDown':
                selectNext();
                break;
            case 'ArrowUp':
                selectPrevious();
                break;
            case 'Enter':
                if (currentIndex >= 0) {
                    e.preventDefault();
                    selectSuggestion(currentSuggestions[currentIndex]);
                }
                else callback?.();

                break;
            case 'Escape':
                hide();
                break;
        }
    }

    function updateActiveStyle() {
        document.querySelectorAll('.suggestion-item').forEach((item, idx) => { item.classList.toggle('active', idx === currentIndex); });
    }

    function scrollToActive() {
        if (currentIndex >= 0) suggestionsList.querySelector(`[data-index="${currentIndex}"]`)?.scrollIntoView({ block: 'nearest' });
    }

    function hideOnClickOutside(e) {
        if (!e.target.closest('.search-box') && !e.target.closest('.suggestions-container')) hide();
    }

    return {
        init,
        show,
        hide,
        fetchWithDebounce,
        render,
        selectSuggestion,
        handleKeyDown,
        hideOnClickOutside
    };
})();
