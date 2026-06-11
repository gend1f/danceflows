(function () {
    const rootId = "cartRoot";

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatMoney(value) {
        return `${new Intl.NumberFormat("ru-RU").format(value)} ₽`;
    }

    function renderLoading(root) {
        root.innerHTML = '<div class="cart-state">Загружаем корзину...</div>';
    }

    function renderError(root, message) {
        root.innerHTML = `
            <div class="cart-state cart-state-error">
                <h2>Не удалось загрузить корзину</h2>
                <p>${escapeHtml(message)}</p>
                <a href="login.html?next=cart.html" class="btn-hero-primary">Войти</a>
            </div>
        `;
    }

    function renderEmpty(root) {
        root.innerHTML = `
            <div class="cart-state">
                <h2>Корзина пуста</h2>
                <p>Добавьте курс, чтобы оформить заявку на обучение.</p>
                <a href="courses.html" class="btn-hero-primary">Выбрать курс</a>
            </div>
        `;
    }

    function renderCart(root, cart) {
        if (!cart.items || cart.items.length === 0) {
            renderEmpty(root);
            return;
        }

        root.innerHTML = `
            <div class="cart-layout">
                <div class="cart-items">
                    ${cart.items.map((item) => `
                        <article class="cart-item">
                            <div class="cart-item-main">
                                <span class="course-level">${escapeHtml(item.course.level)}</span>
                                <h2>${escapeHtml(item.course.title)}</h2>
                                <p>${escapeHtml(item.course.duration)} · ${escapeHtml(item.course.groupSize)}</p>
                            </div>
                            <div class="cart-item-side">
                                <div class="cart-item-price">${formatMoney(item.course.priceMonthly)}<span>/мес</span></div>
                                <button type="button" class="btn-cart-remove" data-remove-cart-item="${item.id}">
                                    Удалить
                                </button>
                            </div>
                        </article>
                    `).join("")}
                </div>

                <aside class="cart-summary">
                    <h2>Итого</h2>
                    <div class="cart-summary-row">
                        <span>Курсов</span>
                        <strong>${cart.count}</strong>
                    </div>
                    <div class="cart-summary-row">
                        <span>Стоимость в месяц</span>
                        <strong>${formatMoney(cart.total)}</strong>
                    </div>
                    <button type="button" class="btn-submit" id="checkoutButton">Оформить заявку</button>
                    <p class="cart-note">После оформления администратор свяжется с вами для подтверждения расписания.</p>
                </aside>
            </div>
        `;
    }

    async function loadCart() {
        const root = document.getElementById(rootId);
        if (!root) {
            return;
        }

        renderLoading(root);
        try {
            const cart = await window.DanceFlowAPI.cart.get();
            renderCart(root, cart);
            if (window.DanceFlowApp) {
                await window.DanceFlowApp.refreshCartCount();
            }
        } catch (error) {
            renderError(root, error.message);
        }
    }

    async function removeItem(itemId) {
        const root = document.getElementById(rootId);
        if (!root) {
            return;
        }

        const cart = await window.DanceFlowAPI.cart.remove(itemId);
        renderCart(root, cart);
        if (window.DanceFlowApp) {
            await window.DanceFlowApp.refreshCartCount();
        }
    }

    async function checkout() {
        const button = document.getElementById("checkoutButton");
        if (button) {
            button.disabled = true;
            button.classList.add("is-loading");
        }

        try {
            const result = await window.DanceFlowAPI.cart.checkout();
            const root = document.getElementById(rootId);
            if (root) {
                root.innerHTML = `
                    <div class="cart-state cart-state-success">
                        <h2>Заявка оформлена</h2>
                        <p>Номер заявки: ${result.order.id}. Мы свяжемся с вами для подтверждения.</p>
                        <a href="courses.html" class="btn-hero-primary">Вернуться к курсам</a>
                    </div>
                `;
            }
            if (window.DanceFlowApp) {
                await window.DanceFlowApp.refreshCartCount();
            }
        } catch (error) {
            alert(error.message);
        } finally {
            if (button) {
                button.disabled = false;
                button.classList.remove("is-loading");
            }
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        loadCart();

        document.addEventListener("click", (event) => {
            const removeButton = event.target.closest("[data-remove-cart-item]");
            if (removeButton) {
                removeItem(removeButton.dataset.removeCartItem);
                return;
            }

            if (event.target.closest("#checkoutButton")) {
                checkout();
            }
        });
    });
})();
