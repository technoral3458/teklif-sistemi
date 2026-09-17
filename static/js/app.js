// ============================================================
// B2B Teklif Sistemi - Main Application JavaScript
// ============================================================

// ── Theme Management ─────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
  // Apply saved theme
  const savedTheme = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);

  // Auto-hide alerts
  initAlerts();

  // Click outside modal closes it
  initModalOverlay();

  // Image preview
  initImagePreview();
});

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const btn = document.getElementById("themeToggleBtn");
  if (!btn) return;
  if (theme === "dark") {
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
    btn.title = "Aydınlık Temaya Geç";
  } else {
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
    btn.title = "Karanlık Temaya Geç";
  }
}

// ── Sidebar Mobile Toggle ─────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.querySelector(".overlay");
  if (!sidebar) return;
  sidebar.classList.toggle("sidebar-open");
  if (overlay) overlay.classList.toggle("overlay-active");
}

// Close sidebar when overlay is clicked
document.addEventListener("DOMContentLoaded", function () {
  const overlay = document.querySelector(".overlay");
  if (overlay) {
    overlay.addEventListener("click", function () {
      const sidebar = document.querySelector(".sidebar");
      if (sidebar) sidebar.classList.remove("sidebar-open");
      overlay.classList.remove("overlay-active");
    });
  }
});

// ── Tab Switching ─────────────────────────────────────────────
function switchTab(tabId) {
  // Hide all tab panes
  document.querySelectorAll(".tab-pane").forEach(function (pane) {
    pane.classList.remove("active");
    pane.style.display = "none";
  });

  // Deactivate all tab buttons
  document.querySelectorAll(".tab-btn").forEach(function (btn) {
    btn.classList.remove("active");
  });

  // Show selected pane
  const target = document.getElementById(tabId);
  if (target) {
    target.classList.add("active");
    target.style.display = "block";
  }

  // Activate matching button
  const activeBtn = document.querySelector(`[data-tab="${tabId}"]`);
  if (activeBtn) activeBtn.classList.add("active");
}

// Initialize tabs on page load — respect active class set in HTML
document.addEventListener("DOMContentLoaded", function () {
  const panes = document.querySelectorAll(".tab-pane");
  if (!panes.length) return;

  const activeBtn = document.querySelector(".tab-btn.active");
  const targetId = activeBtn ? activeBtn.getAttribute("data-tab") : null;

  panes.forEach(function (p) {
    const show = targetId ? p.id === targetId : false;
    p.style.display = show ? "block" : "none";
    p.classList.toggle("active", show);
  });

  if (!targetId) {
    // Fallback: show first pane, activate first button
    panes[0].style.display = "block";
    panes[0].classList.add("active");
    const firstBtn = document.querySelector(".tab-btn");
    if (firstBtn) firstBtn.classList.add("active");
  }
});

// ── Modal ─────────────────────────────────────────────────────
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

function initModalOverlay() {
  document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
    if (overlay.dataset.static === "true") return;
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) {
        overlay.classList.remove("active");
        document.body.style.overflow = "";
      }
    });
  });

  // Close on Escape key
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay.active").forEach(function (m) {
        m.classList.remove("active");
        document.body.style.overflow = "";
      });
    }
  });
}

// ── Flash / Alert Auto-Hide ───────────────────────────────────
function initAlerts() {
  document.querySelectorAll(".alert").forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.5s ease";
      alert.style.opacity = "0";
      setTimeout(function () {
        if (alert.parentNode) alert.parentNode.removeChild(alert);
      }, 500);
    }, 5000);
  });
}

// ── Confirm Delete ────────────────────────────────────────────
function confirmDelete(form) {
  const msg =
    form.getAttribute("data-confirm") ||
    "Bu kaydı silmek istediğinizden emin misiniz?";
  if (window.confirm(msg)) {
    form.submit();
  }
  return false;
}

// ── Image Preview on File Input ───────────────────────────────
function initImagePreview() {
  document.querySelectorAll('input[type="file"][data-preview]').forEach(function (input) {
    input.addEventListener("change", function () {
      const previewId = input.getAttribute("data-preview");
      const preview = document.getElementById(previewId);
      if (!preview) return;
      const file = input.files[0];
      if (file && file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = function (e) {
          preview.src = e.target.result;
          preview.style.display = "block";
        };
        reader.readAsDataURL(file);
      }
    });
  });
}

// Also allow calling manually
function previewImage(inputEl, previewId) {
  const preview = document.getElementById(previewId);
  if (!preview) return;
  const file = inputEl.files[0];
  if (file && file.type.startsWith("image/")) {
    const reader = new FileReader();
    reader.onload = function (e) {
      preview.src = e.target.result;
      preview.style.display = "block";
    };
    reader.readAsDataURL(file);
  }
}

// ── Toast Notifications ───────────────────────────────────────
function showToast(msg, type) {
  type = type || "info";
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText =
      "position:fixed;top:70px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;";
    document.body.appendChild(container);
  }

  const colors = {
    success: "#22c55e",
    error: "#ef4444",
    warning: "#f59e0b",
    info: "#3b82f6",
  };
  const color = colors[type] || colors.info;

  const toast = document.createElement("div");
  toast.style.cssText = `
    background: var(--surface-2, #1e293b);
    color: var(--text-primary, #f1f5f9);
    border-left: 4px solid ${color};
    padding: 12px 16px;
    border-radius: 6px;
    min-width: 240px;
    max-width: 360px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    font-size: 14px;
    opacity: 0;
    transform: translateX(20px);
    transition: all 0.3s ease;
  `;
  toast.textContent = msg;
  container.appendChild(toast);

  // Animate in
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      toast.style.opacity = "1";
      toast.style.transform = "translateX(0)";
    });
  });

  // Auto-remove after 3s
  setTimeout(function () {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 3000);
}

// ── Utility: Format Currency ──────────────────────────────────
function formatCurrency(amount, currency) {
  currency = currency || "USD";
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

// ── Utility: Debounce ─────────────────────────────────────────
function debounce(fn, delay) {
  let timer;
  return function () {
    clearTimeout(timer);
    timer = setTimeout(fn.apply.bind(fn, this, arguments), delay);
  };
}

// ── Search Filter (client-side table filter) ──────────────────
function initTableSearch(inputId, tableId) {
  const input = document.getElementById(inputId);
  const table = document.getElementById(tableId);
  if (!input || !table) return;
  input.addEventListener(
    "input",
    debounce(function () {
      const query = input.value.toLowerCase();
      table.querySelectorAll("tbody tr").forEach(function (row) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? "" : "none";
      });
    }, 200)
  );
}

document.addEventListener("DOMContentLoaded", function () {
  // Auto-init table search if elements exist
  initTableSearch("tableSearch", "mainTable");
});
