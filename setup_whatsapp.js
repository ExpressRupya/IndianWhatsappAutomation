require("dotenv").config();
const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
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
const chromePath = process.env.CHROME_PATH;
if (chromePath) {
  puppeteerOpts.executablePath = chromePath;
}

process.on("unhandledRejection", (err) => {
  console.error("Unhandled rejection:", err?.message);
  process.exit(1);
});

const client = new Client({
  authStrategy: new LocalAuth({ clientId: "dc_news_bot", rmMaxRetries: 10 }),
  puppeteer: puppeteerOpts,
});

let qrShown = false;

client.on("qr", (qr) => {
  if (!qrShown) {
    console.log("SCAN THE QR CODE BELOW WITH YOUR WHATSAPP:");
    qrcode.generate(qr, { small: true });
    qrShown = true;
  }
});

client.on("ready", async () => {
  console.log("\nWhatsApp authenticated! Session saved.");
  console.log("You can now run the daily automation.");
  await client.destroy();
  process.exit(0);
});

client.on("auth_failure", (msg) => {
  console.log("Auth failed:", msg);
  process.exit(1);
});

client.on("disconnected", (reason) => {
  console.log("Disconnected:", reason);
  process.exit(1);
});

setTimeout(() => {
  console.log("\nQR code not scanned within 60 seconds. Run again when ready.");
  process.exit(1);
}, 60000);

client.initialize();
