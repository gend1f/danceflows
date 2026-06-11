(function () {
    const API_BASE = window.DANCEFLOW_API_BASE || "/api";

    function buildUrl(path) {
        return `${API_BASE}${path}`;
    }

    async function request(path, options = {}) {
        const headers = options.headers ? { ...options.headers } : {};
        const requestOptions = {
            method: options.method || "GET",
            headers,
            credentials: "include",
        };

        if (options.body !== undefined) {
            headers["Content-Type"] = "application/json";
            requestOptions.body = JSON.stringify(options.body);
        }

        const response = await fetch(buildUrl(path), requestOptions);
        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json")
            ? await response.json()
            : await response.text();

        if (!response.ok) {
            const message = data && data.detail ? data.detail : "Ошибка запроса";
            const error = new Error(message);
            error.status = response.status;
            error.data = data;
            throw error;
        }

        return data;
    }

    window.DanceFlowAPI = {
        auth: {
            login(payload) {
                return request("/auth/login", {
                    method: "POST",
                    body: payload,
                });
            },
            register(payload) {
                return request("/auth/register", {
                    method: "POST",
                    body: payload,
                });
            },
            me() {
                return request("/auth/me");
            },
            logout() {
                return request("/auth/logout", {
                    method: "POST",
                });
            },
        },
        courses: {
            list() {
                return request("/courses");
            },
        },
        cart: {
            get() {
                return request("/cart");
            },
            add(courseId) {
                return request("/cart/items", {
                    method: "POST",
                    body: { courseId },
                });
            },
            remove(itemId) {
                return request(`/cart/items/${itemId}`, {
                    method: "DELETE",
                });
            },
            checkout() {
                return request("/cart/checkout", {
                    method: "POST",
                });
            },
        },
    };
})();
