require("dotenv").config();
const { Client, LocalAuth } = require("whatsapp-web.js");
const fs = require("fs");
const path = require("path");

const sessionDir = path.resolve(__dirname, ".wwebjs_auth", "session-dc_news_bot");
["SingletonLock", "SingletonSocket", "first_party_sets.db-journal"].forEach((f) => {
  try { fs.unlinkSync(path.join(sessionDir, f)); } catch (_) {}
});

let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", async () => {
  const payload = JSON.parse(input);
  const phoneNumber = payload.phone_number;
  const message = payload.message || "";

  if (!message) {
    console.log("SEND_ERROR: Empty message");
    process.exit(1);
  }

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
    console.log("SEND_ERROR:Initialization timed out after 90s");
    process.exit(1);
  }, 90000);

  client.on("qr", () => {
    console.log("QR_CODE_REQUIRED");
    setTimeout(() => { console.log("QR_TIMEOUT"); process.exit(1); }, 30000);
  });

  client.on("ready", async () => {
    clearTimeout(initTimeout);
    try {
      await client.sendMessage(phoneNumber, message);
      console.log("MESSAGE_SENT");
    } catch (err) {
      console.log("SEND_ERROR:" + err.message);
    }
    await client.destroy();
    process.exit(0);
  });

  client.on("auth_failure", (msg) => { clearTimeout(initTimeout); console.log("AUTH_FAILURE:" + msg); process.exit(1); });
  client.on("disconnected", (reason) => { clearTimeout(initTimeout); console.log("SEND_ERROR:Disconnected:" + reason); process.exit(1); });

  client.initialize();
});
