const Utils = (function () {
    function calculateDistance(lat1, lng1, lat2, lng2) {
        const R = 6371; // Raio da Terra em km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    function isValidCoord(lat, lng) { return isValidLat(lat) && isValidLng(lng); }

    function isValidLat(lat) {
        const latitude = parseFloat(lat);
        return !isNaN(latitude) && latitude >= -90 && latitude <= 90;
    }

    function isValidLng(lng) {
        const longitude = parseFloat(lng);
        return !isNaN(longitude) && longitude >= -180 && longitude <= 180;
    }

    function truncate(text, maxLength = 50) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '…';
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function createElement(tag, className = '', content = '') {
        const el = document.createElement(tag);
        if (className) el.className = className;
        if (typeof content === 'string') el.textContent = content;
        else if (content instanceof HTMLElement) el.appendChild(content);

        return el;
    }

    function remove(selector) {
        const el = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (el?.parentNode) el.parentNode.removeChild(el);
    }

    function formatDistance(meters) {
        if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
        else return `${(meters).toFixed(0)} m`;
    }

    function formatDuration(seconds) {
        const totalMinutes = Math.round(seconds / 60);
        return `${ath.floor(totalMinutes / 60)}:${String(totalMinutes % 60).padStart(2, '0')}`;
    }

    function getCardinalDirection(bearing) { return ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round(bearing / 45) % 8]; }

    function getResiduoId(tipo) {
        for (const id in Constants.RESIDUOS_IDS) {
            if (Constants.RESIDUOS_IDS[id] === tipo) return id;
        }
        return null;
    }

    function getAllResiduoType() {
        const types = [];
        for (const id in Constants.RESIDUOS_IDS) {
            types.push(Constants.TIPOS_RESIDUOS[id]);
        }
        return types;
    }

    function getResiduoIdsForTypes(tipos) {
        const ids = [];
        for (const tipo in tipos) {
            ids.push(getResiduoId(tipo));
        }
        return ids;
    }

    function getTiposPesquisa() {
        return Object.keys(Constants.TIPOS);
    }

    return {
        calculateDistance,
        isValidCoord,
        isValidLat,
        isValidLng,
        truncate,
        escapeHtml,
        createElement,
        remove,
        formatDistance,
        formatDuration,
        getCardinalDirection,
        getResiduoId,
        getAllResiduoType,
        getResiduoIdsForTypes,
        getTiposPesquisa
    };
})();
