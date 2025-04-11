const toggleButton = document.getElementById("toggleMode");
  const body = document.body;

  toggleButton.addEventListener("click", () => {
    body.classList.toggle("dark-mode");
  });
