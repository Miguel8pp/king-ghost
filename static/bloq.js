const toggleButton = document.getElementById("toggle-theme");

    toggleButton.addEventListener("click", () => {
        document.body.classList.toggle("dark");
        localStorage.setItem("theme", document.body.classList.contains("dark") ? "dark" : "light");
    });

    // Al cargar la página, aplica el tema guardado
    window.onload = () => {
        const savedTheme = localStorage.getItem("theme");
        if (savedTheme === "dark") {
            document.body.classList.add("dark");
        }
    };