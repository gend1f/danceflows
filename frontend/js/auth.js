(function () {
    function getMessageNode(form) {
        let message = form.querySelector(".form-message");
        if (!message) {
            message = document.createElement("div");
            message.className = "form-message";
            const submit = form.querySelector('button[type="submit"]');
            form.insertBefore(message, submit);
        }
        return message;
    }

    function setMessage(form, type, text) {
        const message = getMessageNode(form);
        message.className = `form-message ${type ? `form-message-${type}` : ""}`;
        message.textContent = text || "";
        message.hidden = !text;
    }

    function setLoading(form, isLoading) {
        const button = form.querySelector('button[type="submit"]');
        if (!button) {
            return;
        }

        button.disabled = isLoading;
        button.classList.toggle("is-loading", isLoading);
    }

    function nextPage(defaultPage) {
        const params = new URLSearchParams(window.location.search);
        return params.get("next") || defaultPage;
    }

    window.handleLogin = async function (event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);
        setMessage(form, "", "");
        setLoading(form, true);

        try {
            await window.DanceFlowAPI.auth.login({
                email: String(formData.get("email") || ""),
                password: String(formData.get("password") || ""),
                remember: formData.get("remember") === "on",
            });

            window.location.href = nextPage("courses.html");
        } catch (error) {
            setMessage(form, "error", error.message);
        } finally {
            setLoading(form, false);
        }
    };

    window.handleRegister = async function (event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);
        const password = String(formData.get("password") || "");
        const confirmPassword = String(formData.get("confirmPassword") || "");

        setMessage(form, "", "");

        if (password !== confirmPassword) {
            setMessage(form, "error", "Пароли не совпадают");
            return;
        }

        setLoading(form, true);

        try {
            await window.DanceFlowAPI.auth.register({
                firstName: String(formData.get("firstName") || ""),
                lastName: String(formData.get("lastName") || ""),
                email: String(formData.get("email") || ""),
                phone: String(formData.get("phone") || ""),
                password,
            });

            window.location.href = nextPage("courses.html");
        } catch (error) {
            setMessage(form, "error", error.message);
        } finally {
            setLoading(form, false);
        }
    };
})();
