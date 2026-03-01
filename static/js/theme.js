/**
 * Selector de tema Condocdat
 * Persiste la preferencia en localStorage y aplica data-theme en <html>.
 * Valores guardados: 'light' | 'dark' | 'system'
 * data-theme en <html> siempre es 'light' o 'dark' (para aplicar CSS).
 */
(function () {
  var STORAGE_KEY = 'condocdat-theme';

  function getStored() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'system';
    } catch (e) {
      return 'system';
    }
  }

  function setStored(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (e) {}
  }

  function getEffectiveTheme() {
    var stored = getStored();
    if (stored === 'light' || stored === 'dark') return stored;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    return 'light';
  }

  function applyTheme() {
    var effective = getEffectiveTheme();
    document.documentElement.setAttribute('data-theme', effective);
    updateButtons();
  }

  function updateButtons() {
    var stored = getStored();
    document.querySelectorAll('.theme-switcher-buttons [data-theme-value]').forEach(function (btn) {
      var value = btn.getAttribute('data-theme-value');
      btn.setAttribute('aria-pressed', value === stored ? 'true' : 'false');
    });
  }

  function init() {
    applyTheme();

    document.querySelectorAll('.theme-switcher-buttons [data-theme-value]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var value = this.getAttribute('data-theme-value');
        setStored(value);
        applyTheme();
      });
    });

    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
        if (getStored() === 'system') applyTheme();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
