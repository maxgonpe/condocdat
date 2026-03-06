/**
 * Panel lateral colapsable. Guarda estado en localStorage (condocdat-sidebar-open).
 */
(function () {
  var STORAGE_KEY = 'condocdat-sidebar-open';

  function getStored() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      return v === null || v === 'true';
    } catch (e) {
      return true;
    }
  }

  function setStored(open) {
    try {
      localStorage.setItem(STORAGE_KEY, open ? 'true' : 'false');
    } catch (e) {}
  }

  function setSidebarOpen(open) {
    if (open) {
      document.body.classList.remove('sidebar-collapsed');
    } else {
      document.body.classList.add('sidebar-collapsed');
    }
    setStored(open);
  }

  function init() {
    var btnToggle = document.getElementById('sidebar-toggle');
    var btnReopen = document.getElementById('sidebar-reopen');

    if (!getStored()) {
      document.body.classList.add('sidebar-collapsed');
    }

    if (btnToggle) {
      btnToggle.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        setSidebarOpen(false);
        return false;
      });
    }

    if (btnReopen) {
      btnReopen.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        setSidebarOpen(true);
        return false;
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
