const https = require('https');

// Obtener argumentos de la línea de comandos
const args = process.argv.slice(2);
const uid = args[0];
const region = args[1] || 'br'; // Región por defecto: 'br'

const key = 'MigPonc';

// Construir URL de la API
const url = `https://ff.deaddos.online/api/data?region=${region}&uid=${uid}&key=${key}`;

// Realizar solicitud HTTPS GET
https.get(url, (res) => {
    let data = '';

    // Acumular datos recibidos
    res.on('data', chunk => {
        data += chunk;
    });

    // Procesar datos al final
    res.on('end', () => {
        try {
            const json = JSON.parse(data);

            // Imprimir todos los datos recibidos
            console.log(JSON.stringify(json, null, 2)); // pretty-print con indentación

        } catch (e) {
            console.error('❌ Error al parsear JSON:', e.message);
            process.exit(1);
        }
    });

}).on('error', (err) => {
    console.error('❌ Error en la solicitud:', err.message);
    process.exit(1);
});
