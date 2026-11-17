'use strict';
const button = document.getElementById('health-button');
const label = document.getElementById('health-label');
const live = document.getElementById('health-live');
button.addEventListener('click', async () => {
  button.disabled = true;
  label.textContent = 'Kontrol ediliyor…';
  try {
    const response = await fetch('/healthz', { cache: 'no-store', signal: AbortSignal.timeout(5000) });
    const data = await response.json();
    if (!response.ok || data.status !== 'ok') throw new Error('not-ready');
    label.textContent = 'Geçit hazır';
    live.textContent = 'Geçit ve sing-box dinleyicisi hazır. Bu kontrol uçtan uca bağlantı testi değildir.';
  } catch (_) {
    label.textContent = 'Henüz hazır değil';
    live.textContent = 'Geçit kontrol edilemedi. Servis uyuyor veya başlatılıyor olabilir.';
  } finally {
    button.disabled = false;
    button.textContent = 'Yeniden kontrol et ↗';
  }
});
// Intentionally no polling, analytics, artificial keep-alive, or secret fields.
