document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('.contacto-form');
    const submitBtn = form ? form.querySelector('button[type="submit"]') : null;

    if (form && submitBtn) {
        form.addEventListener('submit', function (e) {
            // Desabilitar o botão durante o envio
            submitBtn.disabled = true;
            submitBtn.classList.add('loading');

            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Enviando...';

            // Remover a classe loading após 3 segundos (tempo máximo de resposta esperado)
            const timeout = setTimeout(function () {
                submitBtn.disabled = false;
                submitBtn.classList.remove('loading');
                submitBtn.textContent = originalText;
            }, 3000);

            // Se o form for enviado com sucesso, o servidor redirecionará
            // Se houver erro, o timeout re-habilita o botão
            form.addEventListener('submit', function () {
                clearTimeout(timeout);
            }, { once: true });
        });
    }
});
