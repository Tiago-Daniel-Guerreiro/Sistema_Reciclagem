document.addEventListener('DOMContentLoaded', function () {
    const resendBtn = document.getElementById('resend-btn');
    const resendMessage = document.getElementById('resend-message');
    const emailInput = document.getElementById('email');

    if (resendBtn) {
        resendBtn.addEventListener('click', function (e) {
            e.preventDefault();

            const email = emailInput.value.trim();

            if (!email) {
                showResendMessage('Por favor, insira o email', 'error');
                return;
            }

            // Desabilitar botão durante o envio
            resendBtn.disabled = true;
            resendBtn.textContent = 'Enviando...';

            // Enviar requisição
            fetch('/reenviar-codigo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: email })
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.erro || 'Erro ao enviar');
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    showResendMessage('✓ódigo reenviado com sucesso! Verifica o teu email.', 'success');
                    resendBtn.textContent = 'Reenviar Código';
                    resendBtn.disabled = false;

                    // Resetar depois de 5 segundos
                    setTimeout(() => {
                        resendMessage.style.display = 'none';
                    }, 5000);
                })
                .catch(error => {
                    let mensagem = error.message;

                    if (mensagem.includes('usuario_nao_encontrado')) {
                        mensagem = 'Email não encontrado no sistema.';
                    } else if (mensagem.includes('email_ja_verificado')) {
                        mensagem = 'Este email já foi verificado!';
                    } else if (mensagem.includes('email_nao_enviado')) {
                        mensagem = 'Erro ao enviar email. Tenta novamente mais tarde.';
                    }

                    showResendMessage('✗ ' + mensagem, 'error');
                    resendBtn.textContent = 'Reenviar Código';
                    resendBtn.disabled = false;
                });
        });
    }

    function showResendMessage(message, type) {
        resendMessage.textContent = message;
        resendMessage.className = 'resend-message ' + (type === 'success' ? 'success' : 'error');
        resendMessage.style.display = 'block';
    }
});
