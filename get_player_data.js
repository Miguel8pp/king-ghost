const { uid } = require('free-fire-apis');

const loginId = process.argv[2];

if (!loginId) {
  console.error(JSON.stringify({ error: "Debes proporcionar un UID" }));
  process.exit(1);
}

uid(loginId)
  .then(data => {
    console.log(JSON.stringify(data)); // SOLO imprime JSON válido
  })
  .catch(error => {
    console.error(JSON.stringify({ error: error.message || "Error desconocido" }));
    process.exit(1);
  });
