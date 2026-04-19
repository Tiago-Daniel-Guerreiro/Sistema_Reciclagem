const RoutesRenderer = (function () {
    let stepsDiv = null;  // Cache element

    function displayRoute(route) {
        if (!stepsDiv) stepsDiv = document.getElementById('route-steps');
        if (!stepsDiv) return;

        const routeInfo = document.getElementById('route-info');
        if (routeInfo) routeInfo.style.display = 'none';

        if (!route) return;

        if (!route.legs || route.legs.length === 0) {
            stepsDiv.innerHTML = '<div class="route-empty">Sem dados de rota disponíveis</div>';
            return;
        }

        // Recolher todos os steps
        const allSteps = [];
        route.legs.forEach(leg => { if (leg.steps) leg.steps.forEach(s => allSteps.push(s)); });

        // Construir HTML e renderizar
        const { html, visibleSteps } = buildStepsHTML(allSteps, calculateRouteTotals(route));
        renderStepsWithDelegation(stepsDiv, html, visibleSteps);
    }

    function calculateRouteTotals(route) {
        let totalDistance = 0;
        route.legs.forEach(leg => { totalDistance += leg.distance; });

        return {
            distance: totalDistance,
            distText: Utils.formatDistance(totalDistance)
        };
    }

    function buildStepsHTML(allSteps, totals) {
        let items = '';
        let stepNum = 0;
        const visibleSteps = [];

        allSteps.forEach((step, rawIdx) => {
            if (step.distance === 0 && step.maneuver?.type === 'depart') return;

            const isArrive = step.maneuver?.type === 'arrive';
            if (!isArrive) stepNum++;

            const lat = step.intersections?.[0]?.location?.[1];
            const lng = step.intersections?.[0]?.location?.[0];

            if (!Utils.isValidCoord(lat, lng)) return;

            items += `
                <li class="route-step" ${lat && lng ? `data-lat="${lat}" data-lng="${lng}"` : ''}>
                    <span class="route-step-icon">${getManeuverIcon(step.maneuver?.type || 'straight')}</span>
                    <span class="route-step-text">${generateInstruction(step, stepNum)}</span>
                    <span class="route-step-distance">${Utils.formatDistance(step.distance)}</span>
                </li>`;

            visibleSteps.push(step);
        });

        const html = `
            <div class="route-directions">
                <div id="route-info">
                    Distância:
                    <span id="route-distance">${totals.distText}</span>
                </div>
                <div class="route-directions-header">Direções</div>
                <ol class="route-steps-list">${items}</ol>
            </div>`;

        return { html, visibleSteps };
    }

    function renderStepsWithDelegation(container, html, visibleSteps) {
        container.innerHTML = html;

        // Single event delegation for all route steps
        container.addEventListener('click', (e) => {
            const stepEl = e.target.closest('.route-step[data-lat]');
            if (!stepEl) return;

            const lat = parseFloat(stepEl.dataset.lat);
            const lng = parseFloat(stepEl.dataset.lng);

            if (!Utils.isValidCoord(lat, lng)) return;

            // Remove destaque anterior
            const previousActive = container.querySelector('.route-step.active');
            if (previousActive) previousActive.classList.remove('active');

            // Marca novo como ativo
            stepEl.classList.add('active');
            stepEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

            // Extrai coordenadas do segmento e destaca
            const stepIndex = Array.from(container.querySelectorAll('.route-step')).indexOf(stepEl);
            if (visibleSteps[stepIndex]?.geometry?.coordinates) {
                RoutesMapDrawer.highlightSegment(visibleSteps[stepIndex].geometry.coordinates.map(c => [c[1], c[0]]));
                MapModule.getMap().setView([lat, lng], 14);
            }
        });
    }

    function generateInstruction(step, stepNum) {
        const maneuver = step.maneuver;
        const name = step.name || '?';
        const bearing = maneuver?.bearing_after || 0;
        let result;

        switch (maneuver?.type) {
            case 'depart': result = `Sair pela ${name}`; break;
            case 'arrive': result = 'Chegou ao destino'; break;
            case 'turn': result = `Virar à ${maneuver.modifier === 'left' ? 'esquerda' : 'direita'} na ${name}`; break;
            case 'merge': result = `Incorporar na ${name}`; break;
            case 'ramp': result = `Entrar na via de acesso para ${name}`; break;
            case 'fork': result = `Seguir pela ${maneuver.modifier === 'left' ? 'esquerda' : 'direita'} na ${name}`; break;
            case 'roundabout': result = `Na rotunda, sair pela ${maneuver.exit ? `saída ${maneuver.exit}` : 'primeira saída'} para ${name}`; break;
            default: result = stepNum === 1 ? `Sair pela ${name}` : `Continuar na ${name}`;
        }

        if (bearing) return `${result} em direção ${Utils.getCardinalDirection(bearing)}`;
        return result;
    }

    function getManeuverIcon(maneuverType) {
        const icons = {
            'depart': '▶',
            'arrive': '🏁',
            'turn': '↗',
            'merge': '→',
            'ramp': '⤴',
            'fork': '⤱',
            'roundabout': '↻',
            'straight': '↓'
        };
        return icons[maneuverType] || '→';
    }

    function displayLoading() {
        if (!stepsDiv) stepsDiv = document.getElementById('route-steps');
        if (stepsDiv) stepsDiv.innerHTML = '<div class="loading">Calculando rota...</div>';
    }

    return {
        displayRoute,
        displayLoading,
        generateInstruction,
        getManeuverIcon,
        calculateRouteTotals
    };
})();
