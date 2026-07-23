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
  const groupId = payload.group_id;
  const message = payload.message || "";

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
      console.log("BOT_PHONE: " + (info.phone || "unknown"));
      console.log("BOT_WID: " + info.wid._serialized);
      console.log("PLATFORM: " + info.platform);

      // Check group membership
      const chat = await client.getChatById(groupId);
      console.log("GROUP_NAME: " + chat.name);

      const participants = chat.participants;
      console.log("PARTICIPANTS:");
      for (const p of participants) {
        console.log("  - " + p.id._serialized + " (isAdmin: " + p.isAdmin + ")");
      }

      // Try sending with message ID tracking
      console.log("SENDING_MESSAGE...");
      const sentMsg = await chat.sendMessage(message);
      console.log("SENT_MSG_ID: " + sentMsg.id._serialized);
      console.log("SENT_MSG_ACK: " + sentMsg.ack);
      console.log("SENT_MSG_BODY: " + sentMsg.body.substring(0, 50));
      console.log("SENT_MSG_FROM: " + sentMsg.from);
      console.log("SENT_MSG_TO: " + sentMsg.to);
      console.log("SENT_MSG_IS_SENDER: " + sentMsg.isSender);
      console.log("SENT_MSG_IS_STATUS: " + sentMsg.isStatus);
      console.log("SENT_MSG_TIMESTAMP: " + sentMsg.timestamp);

      // Wait 3 seconds and check if message appears
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Fetch latest messages
      const msgs = await chat.fetchMessages({ limit: 5 });
      console.log("AFTER_SEND_MESSAGES:");
      for (let i = 0; i < msgs.length; i++) {
        const m = msgs[i];
        console.log("  " + i + ": id=" + m.id._serialized + " from=" + m.from + " body=" + (m.body || "").substring(0, 40) + " ack=" + m.ack);
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
