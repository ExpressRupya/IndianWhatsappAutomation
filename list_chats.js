require("dotenv").config();
const { Client, LocalAuth } = require("whatsapp-web.js");
const fs = require("fs");
const path = require("path");

const sessionDir = path.resolve(__dirname, ".wwebjs_auth", "session-dc_news_bot");
["SingletonLock", "SingletonSocket", "first_party_sets.db-journal"].forEach((f) => {
  try { fs.unlinkSync(path.join(sessionDir, f)); } catch (_) {}
});

const puppeteerOpts = {
  headless: true,
  args: ["--no-sandbox", "--disable-gpu", "--disable-features=FirstPartySets"],
};
if (process.env.CHROME_PATH) puppeteerOpts.executablePath = process.env.CHROME_PATH;

const client = new Client({
  authStrategy: new LocalAuth({ clientId: "dc_news_bot", rmMaxRetries: 10 }),
  puppeteer: puppeteerOpts,
});

let initTimeout = setTimeout(() => {
  console.log("TIMEOUT: Initialization took too long");
  process.exit(1);
}, 90000);

client.on("qr", () => {
  console.log("QR_CODE_REQUIRED");
  setTimeout(() => { console.log("QR_TIMEOUT"); process.exit(1); }, 30000);
});

client.on("ready", async () => {
  clearTimeout(initTimeout);
  try {
    const chats = await client.getChats();
    console.log("TOTAL_CHATS: " + chats.length);
    console.log("---TOP 10 CHATS---");
    chats.slice(0, 10).forEach((c, i) => {
      const type = c.isGroup ? "GROUP" : "INDIVIDUAL";
      const id = c.id._serialized || c.id;
      console.log((i+1) + ". [" + type + "] Name: " + (c.name || "(no name)") + " | ID: " + id);
    });
  } catch (err) {
    console.log("ERROR: " + err.message);
  }
  await client.destroy();
  process.exit(0);
});

client.on("auth_failure", (msg) => { clearTimeout(initTimeout); console.log("AUTH_FAILURE:" + msg); process.exit(1); });
client.on("disconnected", (reason) => { clearTimeout(initTimeout); console.log("DISCONNECTED:" + reason); process.exit(1); });

client.initialize();
