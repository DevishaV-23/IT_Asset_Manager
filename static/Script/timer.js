// static/Script/timer.js
document.addEventListener('DOMContentLoaded', () => {
    let timeLeft = 60;
    const timerElement = document.getElementById('timer');
    const btn = document.getElementById('dashboard-btn');

    if (timerElement && btn) {
        const countdown = setInterval(() => {
            timeLeft--;
            timerElement.textContent = timeLeft;

            if (timeLeft <= 0) {
                clearInterval(countdown);
                timerElement.parentElement.innerHTML = "You may now try again.";
                btn.style.backgroundColor = "#2481f4"; 
                btn.style.pointerEvents = "auto";
                btn.style.cursor = "pointer";
            }
        }, 1000);
    }
});