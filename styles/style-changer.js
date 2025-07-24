(() => {
    const themes = {
        nrw: 'new_wave.css',
        artdeco: 'art_deco.css',
        future: 'furturistic.css',
        memories: 'memories.css',
        popmag: 'pop_magazine.css',
        renaissance: 'renaissance.css',
    };
    const linkEl = document.getElementById('theme-style');
    const menu = document.getElementById('style-menu');
    document.getElementById('style-toggle')
        .addEventListener('click', () => menu.classList.toggle('visible'));
    menu.addEventListener('click', e => {
        const key = e.target.dataset.style;
        if (!themes[key]) return;
        linkEl.href = themes[key];
        localStorage.setItem('usil-theme', key);
        menu.classList.remove('visible');
    });
    const saved = localStorage.getItem('usil-theme');
    if (themes[saved]) linkEl.href = themes[saved];
})();
