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
      console.log("WHOAMI: " + JSON.stringify({
        wid: info.wid,
        phone: info.phone,
        platform: info.platform,
        pushname: info.pushname,
      }));

      const chat = await client.getChatById(groupId);
      console.log("GROUP: " + chat.name);
      console.log("UNREAD_COUNT: " + chat.unreadCount);
      console.log("IS_GROUP: " + chat.isGroup);

      if (chat.isGroup) {
        const participants = chat.participants;
        console.log("PARTICIPANT_COUNT: " + participants.length);
        const me = info.wid._serialized;
        const isMember = participants.some(p => p.id._serialized === me);
        console.log("I_AM_MEMBER: " + isMember);

        // Check last 3 messages
        const messages = await chat.fetchMessages({ limit: 3 });
        console.log("LAST_MESSAGES: " + messages.length);
        messages.forEach((m, i) => {
          console.log("  MSG" + i + ": from=" + (m.from || "unknown") + " body=" + (m.body || "").substring(0, 60) + " timestamp=" + m.timestamp);
        });

        // Try sending
        const result = await chat.sendMessage("Debug test - ignore");
        console.log("SEND_RESULT_ID: " + result.id._serialized);
        console.log("SEND_RESULT_ACK: " + result.ack);
        console.log("SEND_RESULT_TIMESTAMP: " + result.timestamp);
      }
    } catch (err) {
      console.log("ERROR: " + err.message);
      console.log("STACK: " + err.stack);
    }
    await client.destroy();
    process.exit(0);
  });

  client.on("auth_failure", (msg) => { clearTimeout(initTimeout); console.log("AUTH_FAILURE:" + msg); process.exit(1); });
  client.on("disconnected", (reason) => { clearTimeout(initTimeout); console.log("DISCONNECTED:" + reason); process.exit(1); });

  client.initialize();
});
