// Countdown Timer for Locked Capsules
class CountdownTimer {
    constructor() {
        this.timerElement = document.querySelector('.countdown-timer');
        if (!this.timerElement) return;
        
        this.unlockTime = this.timerElement.getAttribute('data-unlock');
        if (!this.unlockTime) return;
        
        this.elements = {
            days: document.getElementById('days'),
            hours: document.getElementById('hours'),
            minutes: document.getElementById('minutes'),
            seconds: document.getElementById('seconds')
        };
        
        this.updateLocalTime();
        this.start();
    }
    
    updateLocalTime() {
        const unlockLocalElement = document.getElementById('unlock-local');
        if (!unlockLocalElement) return;
        
        try {
            const date = new Date(this.unlockTime);
            const options = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Europe/Istanbul'
            };
            unlockLocalElement.textContent = date.toLocaleString('tr-TR', options);
        } catch (e) {
            console.error('Date formatting error:', e);
        }
    }
    
    calculateTimeRemaining() {
        const now = new Date().getTime();
        const unlockDate = new Date(this.unlockTime).getTime();
        const difference = unlockDate - now;
        
        if (difference <= 0) {
            return {
                total: 0,
                days: 0,
                hours: 0,
                minutes: 0,
                seconds: 0
            };
        }
        
        return {
            total: difference,
            days: Math.floor(difference / (1000 * 60 * 60 * 24)),
            hours: Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
            minutes: Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60)),
            seconds: Math.floor((difference % (1000 * 60)) / 1000)
        };
    }
    
    updateDisplay(time) {
        this.elements.days.textContent = String(time.days).padStart(2, '0');
        this.elements.hours.textContent = String(time.hours).padStart(2, '0');
        this.elements.minutes.textContent = String(time.minutes).padStart(2, '0');
        this.elements.seconds.textContent = String(time.seconds).padStart(2, '0');
        
        // Add pulse animation to seconds
        this.elements.seconds.style.animation = 'none';
        setTimeout(() => {
            this.elements.seconds.style.animation = 'pulse 1s ease-in-out';
        }, 10);
    }
    
    start() {
        this.update();
        this.interval = setInterval(() => this.update(), 1000);
    }
    
    update() {
        const time = this.calculateTimeRemaining();
        this.updateDisplay(time);
        
        if (time.total <= 0) {
            clearInterval(this.interval);
            this.onComplete();
        }
    }
    
    onComplete() {
        // Reload page when countdown reaches zero
        setTimeout(() => {
            window.location.reload();
        }, 2000);
        
        // Show completion message
        const countdownSection = document.querySelector('.countdown-section');
        if (countdownSection) {
            countdownSection.innerHTML = `
                <div class="unlocked-section">
                    <div class="unlocked-icon">🎉</div>
                    <h2>Kapsül Açılıyor!</h2>
                    <p>Sayfa yenileniyor...</p>
                </div>
            `;
        }
    }
}

// Initialize countdown on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new CountdownTimer());
} else {
    new CountdownTimer();
}

// File input styling
document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', function() {
        const label = this.nextElementSibling;
        const fileName = this.files[0]?.name || 'Dosya Seç';
        const fileText = label.querySelector('.file-text');
        if (fileText) {
            fileText.textContent = fileName;
        }
    });
});
