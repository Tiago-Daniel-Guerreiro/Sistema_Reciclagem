const ApiService = (function () {
    const BASE_URL = 'https://nominatim.openstreetmap.org';

    async function fetchReverse(lat, lng) {
        const params = new URLSearchParams({
            format: 'json',
            lat,
            lon: lng,
            addressdetails: '1',
            namedetails: '1',
            zoom: '18',
            'accept-language': 'pt'
        });

        try {
            const response = await fetch(`${BASE_URL}/reverse?${params.toString()}`);
            const data = await response.json();
            return data?.error ? null : data;
        } catch (err) {
            console.error('ApiService.fetchReverse error:', err);
            return null;
        }
    }

    async function fetchOsmDetails(osmType, osmId) {
        const params = new URLSearchParams({
            format: 'json',
            osmtype: { 'node': 'N', 'way': 'W', 'relation': 'R' }[osmType] || osmType.charAt(0).toUpperCase(),
            osmid: osmId,
            addressdetails: '1'
        });

        try {
            const response = await fetch(`${BASE_URL}/details?${params.toString()}`);
            const data = await response.json();
            return data?.error ? null : data;
        } catch (err) {
            console.error('ApiService.fetchOsmDetails error:', err);
            return null;
        }
    }

    async function fetchWikipedia(wikiTag) {
        try {
            let lang = 'pt';
            let title = wikiTag;

            // Parse language prefix se existir (ex: en:Article)
            if (wikiTag.includes(':')) {
                const separatorIndex = wikiTag.indexOf(':');
                lang = wikiTag.slice(0, separatorIndex);
                title = wikiTag.slice(separatorIndex + 1);
            }

            // Tentar com o idioma original
            const tryFetch = async (l, t) => {
                const response = await fetch(`https://${l}.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(t)}`);
                return response.ok ? await response.json() : null;
            };

            const result = await tryFetch(lang, title);
            if (result) return result;

            if (lang !== 'pt') return await tryFetch('pt', title);
        } catch (error) { console.error('ApiService.fetchWikipedia error:', error); }

        return null;
    }

    async function resolveDetalhes(baseData) {
        if (!baseData) return null;

        const lat = parseFloat(baseData.lat);
        const lng = parseFloat(baseData.lng);

        if (!Utils.isValidCoord(lat, lng)) {
            console.error('resolveDetalhes error: Coordenadas inválidas');
            return null;
        }

        if (baseData.wikipedia) {
            return { wikipedia: baseData.wikipedia };
        }

        // Busca Wikipedia com timeout
        const wikiPromise = (async () => {
            try {
                const nominatim = await Promise.race([
                    fetchReverse(lat, lng),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 3000))
                ]);

                if (!nominatim) {
                    console.warn('Reverse geocoding sem resposta');
                    return null;
                }

                const osmDetails = await Promise.race([
                    fetchOsmDetails(nominatim.osm_type, nominatim.osm_id),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 3000))
                ]);

                const wikiTag = osmDetails?.extratags?.wikipedia || nominatim?.extratags?.wikipedia;
                if (!wikiTag) return null;

                const wikipedia = await Promise.race([
                    fetchWikipedia(wikiTag),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000))
                ]);

                return wikipedia;
            } catch (err) {
                console.warn('Wikipedia lookup timeout/failed:', err.message);
                return null;
            }
        })();

        const wikipedia = await wikiPromise;

        return {
            wikipedia: wikipedia ? {
                title: wikipedia.title,
                extract: wikipedia.extract,
                url: wikipedia.content_urls?.desktop?.page || `https://pt.wikipedia.org/wiki/${encodeURIComponent(wikipedia.title)}`
            } : null
        };
    }

    return {
        fetchReverse,
        fetchOsmDetails,
        fetchWikipedia,
        resolveDetalhes
    };
})();
