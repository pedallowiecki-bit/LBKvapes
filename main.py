const { Client, GatewayIntentBits, SlashCommandBuilder, EmbedBuilder, ChannelType, PermissionFlagsBits } = require('discord.js');

const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers] });

// --- KONFIGURACJA ZMIENNYCH ---
// Zamiast wpisywać token na sztywno, bot pobierze go z ustawień hostingu
const TOKEN = process.env.DISCORD_TOKEN; 

const ROLE_PRO_ID = '1512520808839381012';
const ROLE_ULTRA_ID = '1512520692015562812';

const CD_UZER = 5 * 60 * 60 * 1000;
const CD_PRO = 30 * 60 * 1000;
const CD_ULTRA = 30 * 1000;

const cooldowns = new Map();

function generateRandomCode(template) {
    return template.replace(/X/g, () => {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        return chars.charAt(Math.floor(Math.random() * chars.length));
    });
}

function formatTime(ms) {
    const s = Math.ceil(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ${s % 60}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
}

client.once('ready', async () => {
    console.log(`Bot zalogowany na hostingu jako ${client.user.tag}!`);

    const commands = [
        new SlashCommandBuilder().setName('gen-mc').setDescription('Generuje kod podarunkowy do Minecraft'),
        new SlashCommandBuilder().setName('gen-psc').setDescription('Generuje kod zasilający PaySafeCard'),
        new SlashCommandBuilder().setName('gen-roblox').setDescription('Generuje kod na darmowe Robuxy'),
        new SlashCommandBuilder()
            .setName('setup-server')
            .setDescription('Automatycznie tworzy strukturę kanałów i cennik rang generatora')
            .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    ];

    await client.application.commands.set(commands);
    console.log('✅ Komendy zarejestrowane!');
});

client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;

    const { commandName, user, member, guild } = interaction;
    const userId = user.id;

    if (commandName === 'setup-server') {
        await interaction.reply({ content: '⚙️ Rozpoczynam budowanie struktury serwera... Proszę czekać.', ephemeral: true });

        try {
            const mainCategory = await guild.channels.create({
                name: '📢 ▬▬ GŁÓWNA STREFA ▬▬',
                type: ChannelType.GuildCategory,
            });

            const infoChannel = await guild.channels.create({ name: '💬｜regulamin', type: ChannelType.GuildText, parent: mainCategory.id });
            const shopChannel = await guild.channels.create({ name: '🛒｜cennik-rang', type: ChannelType.GuildText, parent: mainCategory.id });
            const proofChannel = await guild.channels.create({ name: '✅｜dowody-legit', type: ChannelType.GuildText, parent: mainCategory.id });

            const genCategory = await guild.channels.create({
                name: '🔑 ▬▬ DARMOWE KODY ▬▬',
                type: ChannelType.GuildCategory,
            });

            await guild.channels.create({ name: '🎮｜gen-minecraft', type: ChannelType.GuildText, parent: genCategory.id });
            await guild.channels.create({ name: '🤖｜gen-roblox', type: ChannelType.GuildText, parent: genCategory.id });
            await guild.channels.create({ name: '💳｜gen-psc', type: ChannelType.GuildText, parent: genCategory.id });

            const priceEmbed = new EmbedBuilder()
                .setColor('#FFD700')
                .setTitle('🛒 SKLEP GENERATORA – OFERTA RANG')
                .setDescription('Chcesz generować kody znacznie częściej bez długiego czekania? Zdobądź wyższą rangę i omiń limity!')
                .addFields(
                    { name: '👤 Ranga: UZER', value: '• **Cena:** `DARMOWA` (Dla każdego)\n• Cooldown: **5 godzin** na komendę\n• Dostęp do podstawowych generatorów.', inline: false },
                    { name: '💎 Ranga: PRO', value: '• **Cena:** `10 PLN` (PSC / Blik / SMS)\n• Cooldown: **Skrócony do 30 minut!**\n• Większa szansa na trafienie działającego kodu.', inline: false },
                    { name: '🔥 Ranga: ULTRA', value: '• **Cena:** `25 PLN` (PSC / Blik)\n• Cooldown: **Zaledwie 30 sekund!** (Brak limitów)\n• Priorytetowe generowanie i unikalny kolor na serwerze.', inline: false }
                )
                .setThumbnail(client.user.displayAvatarURL())
                .setFooter({ text: 'W celu zakupu skontaktuj się z Właścicielem serwera poprzez Ticket / DM!' });

            await shopChannel.send({ embeds: [priceEmbed] });
            return await interaction.editReply({ content: '✅ Serwer został pomyślnie zbudowany!' });

        } catch (error) {
            console.error(error);
            return await interaction.editReply({ content: '❌ Wystąpił błąd podczas budowania serwera. Sprawdź uprawnienia bota.' });
        }
    }

    let userCooldownDuration = CD_UZER; 
    let rankName = 'UZER';

    if (member.roles.cache.has(ROLE_ULTRA_ID)) {
        userCooldownDuration = CD_ULTRA;
        rankName = 'ULTRA';
    } else if (member.roles.cache.has(ROLE_PRO_ID)) {
        userCooldownDuration = CD_PRO;
        rankName = 'PRO';
    }

    const cooldownKey = `${userId}-${commandName}`;
    if (cooldowns.has(cooldownKey)) {
        const expirationTime = cooldowns.get(cooldownKey) + userCooldownDuration;
        const now = Date.now();

        if (now < expirationTime) {
            const timeLeft = expirationTime - now;
            const errorEmbed = new EmbedBuilder()
                .setColor('#FF0000')
                .setTitle('❌ Limit wyczerpany!')
                .setDescription(`Twoja ranga to **${rankName}**. Możesz wygenerować kolejny kod dopiero za:\n⏳ **${formatTime(timeLeft)}**`)
                .setFooter({ text: 'Chcesz generować częściej? Kup wyższą rangę!' });
            
            return interaction.reply({ embeds: [errorEmbed], ephemeral: true });
        }
    }

    let code = '';
    let title = '';

    if (commandName === 'gen-mc') {
        code = generateRandomCode('XXXX-XXXX-XXXX');
        title = '🎮 KOD MINECRAFT';
    } else if (commandName === 'gen-psc') {
        code = generateRandomCode('XXXX-XXXX-XXXX-XXXX');
        title = '💳 KOD PAYSAFECARD';
    } else if (commandName === 'gen-roblox') {
        code = generateRandomCode('XXXX-XXXX-XXXX');
        title = '🤖 KOD ROBLOX ROBUX';
    }

    const dmEmbed = new EmbedBuilder()
        .setColor('#00FF00')
        .setTitle(`${title} WYGENEROWANY!`)
        .setDescription(`Twój kod został pomyślnie wyciągnięty z bazy danych!\n\n**KOD:** \`\`\`${code}\`\`\`\n*Zrealizuj go jak najszybciej.*`)
        .addFields(
            { name: 'Użyta ranga', value: `\`${rankName}\``, inline: true },
            { name: 'Status kodu', value: '🟢 Aktywny', inline: true }
        )
        .setFooter({ text: 'Dzięki za korzystanie z bazy!' });

    try {
        await user.send({ embeds: [dmEmbed] });

        const successChannelEmbed = new EmbedBuilder()
            .setColor('#00FF00')
            .setTitle('✅ Kod wysłany!')
            .setDescription(`Hej ${user}, wygenerowano nowy kod i wysłano go w **wiadomości prywatnej (PV)**! Sprawdź DM. 📬`)
            .setFooter({ text: `Ranga: ${rankName} • Następny za: ${formatTime(userCooldownDuration)}` });

        cooldowns.set(cooldownKey, Date.now());
        await interaction.reply({ embeds: [successChannelEmbed] });

    } catch (error) {
        const errorChannelEmbed = new EmbedBuilder()
            .setColor('#FF0000')
            .setTitle('❌ Błąd wysyłania!')
            .setDescription(`Nie mogłem wysłać kodu do Ciebie, ${user}.\n\n⚠️ **Masz zablokowane wiadomości prywatne (DM) z tego serwera!** Odblokuj je w ustawieniach i spróbuj ponownie.`)
            .setFooter({ text: 'Status: Blokada DM' });

        await interaction.reply({ embeds: [errorChannelEmbed], ephemeral: true });
    }
});

// Zabezpieczenie przed wywaleniem bota, gdy w panelu nie ma tokenu
if (!TOKEN) {
    console.error("❌ BŁĄD: Brak zmiennej DISCORD_TOKEN w konfiguracji hostingu!");
    process.exit(1);
}

client.login(TOKEN);
