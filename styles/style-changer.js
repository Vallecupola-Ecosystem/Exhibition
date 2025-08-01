(() => {
    const prefix = '/Exhibition/styles/';
    const themes = {
        nrw: prefix + 'new_wave.css',
        artdeco: prefix + 'art_deco.css',
        future: prefix + 'furturistic.css',
        memories: prefix + 'memories.css',
        popmag: prefix + 'pop_magazine.css',
        renaissance: prefix + 'renaissance.css',
        default: prefix + 'default.css',
    };
    const STORAGE_KEY = 'exhibition-theme';
    const linkEl = document.getElementById('theme-style');
    const menu = document.getElementById('style-menu');
    document.getElementById('style-toggle')
        .addEventListener('click', () => menu.classList.toggle('visible'));
    menu.addEventListener('click', e => {
        const key = e.target.dataset.style;
        if (!themes[key]) return;
        linkEl.href = themes[key];
        localStorage.setItem(STORAGE_KEY, key);
        menu.classList.remove('visible');
    });
    const saved = localStorage.getItem(STORAGE_KEY);
    if (themes[saved]) linkEl.href = themes[saved];
})();
