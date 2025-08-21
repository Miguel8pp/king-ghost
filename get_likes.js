// get_likes.js
const https = require('https');

const args = process.argv.slice(2);
const uid = args[0];
const url = `https://botlikesff.rexapi.com.br/api/v2/likes?uid=${uid}`;

https.get(url, (res) => {
    let data = '';

    res.on('data', chunk => {
        data += chunk;
    });

    res.on('end', () => {
        try {
            const json = JSON.parse(data);
            console.log(JSON.stringify(json));
        } catch (e) {
            console.error('❌ Error al parsear JSON:', e.message);
            process.exit(1);
        }
    });
}).on('error', (err) => {
    console.error('❌ Error en la solicitud:', err.message);
    process.exit(1);
});
