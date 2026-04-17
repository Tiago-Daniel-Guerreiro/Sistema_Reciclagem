const Format = (function () {
    function isEmpty(value) {
        if (!value) return true;
        if (typeof value === 'string') return value.trim().length === 0;
        if (Array.isArray(value)) return value.filter(item => !isEmpty(item)).length === 0;
        if (value.constructor === Object) return Object.keys(value).filter(key => !isEmpty(value[key])).length === 0;
        return false;
    }

    function firstValid(values) {
        for (const v of values) { if (!isEmpty(v)) return v; }
        return null;
    }

    function isValidUrl(url) {
        url = normalize(url);
        return !isEmpty(url) ? /^(https?:\/\/|\/\/)/.test(url) : false;
    }

    function normalizeArray(arr, calback_normalizer_array) {
        if (!Array.isArray(arr))
            return [];

        if (calback_normalizer_array && typeof calback_normalizer_array === 'function')
            return calback_normalizer_array(arr);

        return removeEmptyInArray(arr.map(item => {
            if (typeof item === 'string') return normalize(item);
        }));;
    }

    function normalize(str) {
        if (isEmpty(str) || typeof str !== 'string') return '';

        return str
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .trim();
    }

    function defaultIfEmpty(value, defaultValue = '') { return isEmpty(value) ? defaultValue : value; }
    function JoinValues(separator, ...values) { return removeEmptyInArray(values).join(separator); }
    function removeEmptyInArray(arr) { return arr.filter(item => item); }

    return {
        isEmpty,
        defaultIfEmpty,
        normalize,
        JoinValues,
        removeEmptyInArray,
        normalizeArray,
        firstValid,
        isValidUrl
    };
})();
