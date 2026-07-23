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
  const groupId = payload.group_id;

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
    console.log("TIMEOUT");
    process.exit(1);
  }, 90000);

  client.on("qr", () => {
    console.log("QR_CODE_REQUIRED");
    setTimeout(() => { process.exit(1); }, 30000);
  });

  client.on("ready", async () => {
    clearTimeout(initTimeout);
    try {
      const info = client.info;
      console.log("BOT_WID: " + info.wid._serialized);
      console.log("PLATFORM: " + info.platform);

      // Test 1: Send to individual number
      console.log("\n--- TEST 1: Send to individual ---");
      try {
        const chat = await client.getChatById(phoneNumber + "@c.us");
        const sent = await chat.sendMessage("Individual test " + Date.now());
        console.log("INDIVIDUAL_ACK: " + sent.ack);
        console.log("INDIVIDUAL_IS_SENDER: " + sent.isSender);
      } catch(e) {
        console.log("INDIVIDUAL_ERROR: " + e.message);
      }

      // Test 2: Send to group by ID
      console.log("\n--- TEST 2: Send to group ---");
      try {
        const groupChat = await client.getChatById(groupId);
        const sent = await groupChat.sendMessage("Group test " + Date.now());
        console.log("GROUP_ACK: " + sent.ack);
        console.log("GROUP_IS_SENDER: " + sent.isSender);
        console.log("GROUP_FROM: " + sent.from);
      } catch(e) {
        console.log("GROUP_ERROR: " + e.message);
      }

      // Test 3: Check if phone is registered
      console.log("\n--- TEST 3: Check number registration ---");
      try {
        const isRegistered = await client.isRegisteredUser(phoneNumber + "@c.us");
        console.log("IS_REGISTERED: " + isRegistered);
      } catch(e) {
        console.log("REGISTER_CHECK_ERROR: " + e.message);
      }

    } catch (err) {
      console.log("ERROR: " + err.message);
    }
    await client.destroy();
    process.exit(0);
  });

  client.on("auth_failure", (msg) => { clearTimeout(initTimeout); console.log("AUTH_FAILURE:" + msg); process.exit(1); });
  client.on("disconnected", (reason) => { clearTimeout(initTimeout); console.log("DISCONNECTED:" + reason); process.exit(1); });

  client.initialize();
});
