import { Client, GatewayIntentBits, Partials, Collection, EmbedBuilder, ButtonBuilder, ButtonStyle, ActionRowBuilder } from 'discord.js';
import { config } from 'dotenv';
import fs from 'fs/promises';

// Load environment variables
config();

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages
  ],
  partials: [Partials.Channel, Partials.Message]
});

// Store active threads
const threads = new Collection();

// Default configuration
const defaultConfig = {
  prefix: '!',
  status: 'DM me for help!',
  guildId: null,
  modmailCategory: null,
  logChannel: null,
  staffRoles: [],
  blockedUsers: [],
  threadCloseTime: 12,
  color: {
    default: 0x5865F2,
    user: 0x2ECC71,
    staff: 0x3498DB,
    error: 0xE74C3C,
    success: 0x2ECC71,
    warning: 0xF1C40F
  }
};

let config = defaultConfig;

// Load config
async function loadConfig() {
  try {
    const data = await fs.readFile('config.json', 'utf8');
    config = { ...defaultConfig, ...JSON.parse(data) };
  } catch (error) {
    console.error('Error loading config:', error);
    await saveConfig();
  }
}

// Save config
async function saveConfig() {
  try {
    await fs.writeFile('config.json', JSON.stringify(config, null, 2));
  } catch (error) {
    console.error('Error saving config:', error);
  }
}

// Handle DM messages
client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  
  if (message.channel.type === 'DM') {
    // Check if user is blocked
    if (config.blockedUsers.includes(message.author.id)) {
      const embed = new EmbedBuilder()
        .setTitle('You are blocked')
        .setDescription('You have been blocked from using the modmail system.')
        .setColor(config.color.error);
      
      await message.author.send({ embeds: [embed] });
      return;
    }

    // Check if thread exists
    const thread = threads.get(message.author.id);
    if (thread) {
      await forwardToThread(message, thread.channelId);
    } else {
      await createThread(message);
    }
  }
});

// Create new thread
async function createThread(message) {
  const guild = client.guilds.cache.get(config.guildId);
  if (!guild) return;

  const category = guild.channels.cache.get(config.modmailCategory);
  if (!category) return;

  // Create channel
  const channel = await guild.channels.create({
    name: `${message.author.username}-${message.author.discriminator}`,
    parent: category,
    topic: `ModMail thread for ${message.author.tag} (${message.author.id})`
  });

  // Create thread object
  const threadData = {
    userId: message.author.id,
    channelId: channel.id,
    createdAt: new Date().toISOString(),
    messages: []
  };

  threads.set(message.author.id, threadData);

  // Create thread controls
  const closeButton = new ButtonBuilder()
    .setCustomId('close_thread')
    .setLabel('Close')
    .setStyle(ButtonStyle.Secondary)
    .setEmoji('🔒');

  const blockButton = new ButtonBuilder()
    .setCustomId('block_user')
    .setLabel('Block User')
    .setStyle(ButtonStyle.Danger)
    .setEmoji('🚫');

  const row = new ActionRowBuilder().addComponents(closeButton, blockButton);

  // Send welcome message
  const embed = new EmbedBuilder()
    .setTitle('New ModMail Thread')
    .setDescription(`Thread created for ${message.author.tag} (${message.author.id})`)
    .setColor(config.color.default)
    .setTimestamp();

  await channel.send({ embeds: [embed], components: [row] });
  await forwardToThread(message, channel.id);

  // Send confirmation to user
  const userEmbed = new EmbedBuilder()
    .setTitle('ModMail Thread Created')
    .setDescription('Your message has been sent to the staff. Please wait for a response.')
    .setColor(config.color.success)
    .setTimestamp();

  await message.author.send({ embeds: [userEmbed] });
}

// Forward message to thread
async function forwardToThread(message, channelId) {
  const channel = client.channels.cache.get(channelId);
  if (!channel) return;

  const embed = new EmbedBuilder()
    .setDescription(message.content || '*No content*')
    .setColor(config.color.user)
    .setAuthor({
      name: message.author.tag,
      iconURL: message.author.displayAvatarURL()
    })
    .setTimestamp();

  const files = Array.from(message.attachments.values());
  await channel.send({ embeds: [embed], files });
}

// Handle button interactions
client.on('interactionCreate', async (interaction) => {
  if (!interaction.isButton()) return;

  const threadId = interaction.message.channel.parentId;
  if (!threadId) return;

  switch (interaction.customId) {
    case 'close_thread':
      await closeThread(interaction);
      break;
    case 'block_user':
      await blockUser(interaction);
      break;
  }
});

// Close thread
async function closeThread(interaction) {
  const userId = interaction.channel.topic?.match(/\((\d+)\)/)?.[1];
  if (!userId) return;

  const thread = threads.get(userId);
  if (!thread) return;

  // Notify user
  const user = await client.users.fetch(userId);
  const embed = new EmbedBuilder()
    .setTitle('Thread Closed')
    .setDescription('This ModMail thread has been closed by a staff member.')
    .setColor(config.color.warning)
    .setTimestamp();

  await user.send({ embeds: [embed] }).catch(() => {});

  // Delete thread data
  threads.delete(userId);

  // Update channel
  await interaction.channel.setName(`closed-${interaction.channel.name}`);
  await interaction.reply({ content: 'Thread closed.', ephemeral: true });
}

// Block user
async function blockUser(interaction) {
  const userId = interaction.channel.topic?.match(/\((\d+)\)/)?.[1];
  if (!userId) return;

  if (!config.blockedUsers.includes(userId)) {
    config.blockedUsers.push(userId);
    await saveConfig();

    // Notify user
    const user = await client.users.fetch(userId);
    const embed = new EmbedBuilder()
      .setTitle('You Have Been Blocked')
      .setDescription('You have been blocked from using the ModMail system.')
      .setColor(config.color.error)
      .setTimestamp();

    await user.send({ embeds: [embed] }).catch(() => {});

    // Close thread
    await closeThread(interaction);

    await interaction.reply({ content: 'User has been blocked.', ephemeral: true });
  } else {
    await interaction.reply({ content: 'User is already blocked.', ephemeral: true });
  }
}

// Client ready event
client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  await loadConfig();
  
  // Set status
  client.user.setActivity(config.status, { type: 'WATCHING' });
});

// Login
client.login(process.env.TOKEN);