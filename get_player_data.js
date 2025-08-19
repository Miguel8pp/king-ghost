const https = require('https');

const args = process.argv.slice(2);
const uid = args[0];
const region = args[1] || 'br'; // Puedes cambiar el valor por defecto si quieres

const key = 'MigPonc';

const url = `https://ff.deaddos.online/api/data?region=${region}&uid=${uid}&key=${key}`;

https.get(url, (res) => {
    let data = '';

    res.on('data', chunk => {
        data += chunk;
    });

    res.on('end', () => {
        try {
            const json = JSON.parse(data);

            // Extraer solo los campos necesarios
            const result = {
                nickname: json.basicInfo.nickname,
                region: json.basicInfo.region,
                accountId: json.basicInfo.accountId
            };

            console.log(JSON.stringify(result));
        } catch (e) {
            console.error('❌ Error al parsear JSON:', e.message);
            process.exit(1);
        }
    });
}).on('error', (err) => {
    console.error('❌ Error en la solicitud:', err.message);
    process.exit(1);
});
