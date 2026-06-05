(function () {
    let currentUser = null;

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function currentPage() {
        const page = window.location.pathname.split("/").pop();
        return page || "index.html";
    }

    function cartLabel(count) {
        return count > 0 ? `Корзина (${count})` : "Корзина";
    }

    function guestDesktopHtml() {
        return `
            <a href="login.html" class="btn-secondary">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4M10 17l5-5-5-5M15 12H3"></path>
                </svg>
                Вход
            </a>
            <a href="register.html" class="btn-primary">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"></path>
                    <circle cx="8.5" cy="7" r="4"></circle>
                    <line x1="20" y1="8" x2="20" y2="14"></line>
                    <line x1="23" y1="11" x2="17" y2="11"></line>
                </svg>
                Регистрация
            </a>
        `;
    }

    function userDesktopHtml(user, count) {
        return `
            <span class="header-user">${escapeHtml(user.firstName)}</span>
            <a href="cart.html" class="btn-secondary cart-link">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6"></path>
                </svg>
                <span data-cart-count-label>${cartLabel(count)}</span>
            </a>
            <button type="button" class="btn-primary" onclick="DanceFlowApp.logout()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"></path>
                    <polyline points="16 17 21 12 16 7"></polyline>
                    <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                Выйти
            </button>
        `;
    }

    function guestMobileHtml() {
        return `
            <a href="login.html" class="btn-mobile">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"></path>
                </svg>
                Вход
            </a>
            <a href="register.html" class="btn-mobile-primary">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"></path>
                    <circle cx="8.5" cy="7" r="4"></circle>
                </svg>
                Регистрация
            </a>
        `;
    }

    function userMobileHtml(user, count) {
        return `
            <div class="mobile-user">${escapeHtml(user.firstName)} ${escapeHtml(user.lastName)}</div>
            <a href="cart.html" class="btn-mobile">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6"></path>
                </svg>
                <span data-cart-count-label>${cartLabel(count)}</span>
            </a>
            <button type="button" class="btn-mobile-primary" onclick="DanceFlowApp.logout()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"></path>
                    <polyline points="16 17 21 12 16 7"></polyline>
                    <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                Выйти
            </button>
        `;
    }

    function renderHeader(user, count) {
        document.querySelectorAll(".header-actions").forEach((node) => {
            node.innerHTML = user ? userDesktopHtml(user, count) : guestDesktopHtml();
        });

        document.querySelectorAll(".mobile-actions").forEach((node) => {
            node.innerHTML = user ? userMobileHtml(user, count) : guestMobileHtml();
        });
    }

    async function loadCurrentUser() {
        try {
            const data = await window.DanceFlowAPI.auth.me();
            currentUser = data.user;
            return currentUser;
        } catch (error) {
            currentUser = null;
            return null;
        }
    }

    async function loadCartCount() {
        if (!currentUser) {
            return 0;
        }

        try {
            const cart = await window.DanceFlowAPI.cart.get();
            return cart.count || 0;
        } catch (error) {
            return 0;
        }
    }

    async function refreshHeader() {
        const user = await loadCurrentUser();
        const count = await loadCartCount();
        renderHeader(user, count);
    }

    async function refreshCartCount() {
        if (!currentUser) {
            return null;
        }

        const cart = await window.DanceFlowAPI.cart.get();
        document.querySelectorAll("[data-cart-count-label]").forEach((node) => {
            node.textContent = cartLabel(cart.count || 0);
        });
        return cart;
    }

    async function logout() {
        await window.DanceFlowAPI.auth.logout();
        currentUser = null;
        window.location.href = "index.html";
    }

    function requireAuth(nextPage) {
        if (currentUser) {
            return true;
        }

        const next = nextPage || currentPage();
        window.location.href = `login.html?next=${encodeURIComponent(next)}`;
        return false;
    }

    window.toggleMobileMenu = window.toggleMobileMenu || function () {
        const nav = document.getElementById("mobileNav");
        if (nav) {
            nav.classList.toggle("active");
        }
    };

    window.DanceFlowApp = {
        refreshHeader,
        refreshCartCount,
        logout,
        requireAuth,
        getCurrentUser() {
            return currentUser;
        },
    };

    document.addEventListener("DOMContentLoaded", refreshHeader);
})();
