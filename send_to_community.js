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
  const COMMUNITY_NAME = payload.community_name || "Express Rupya DC News";
  const message = payload.message || "";

  if (!message) {
    console.log("SEND_ERROR: Empty message");
    process.exit(1);
  }

  const puppeteerOpts = {
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-features=FirstPartySets"],
  };
  const chromePath = process.env.CHROME_PATH;
  if (chromePath) {
    puppeteerOpts.executablePath = chromePath;
  }

  process.on("unhandledRejection", (err) => {
    console.error("SEND_ERROR:Unhandled rejection:", err?.message);
    process.exit(1);
  });

  const client = new Client({
    authStrategy: new LocalAuth({ clientId: "dc_news_bot", rmMaxRetries: 10 }),
    puppeteer: puppeteerOpts,
  });

  let qrTimedOut = false;
  let initTimeout = setTimeout(() => {
    console.log("SEND_ERROR:Initialization timed out after 90s");
    process.exit(1);
  }, 90000);

  client.on("qr", () => {
    console.log("QR_CODE_REQUIRED");
    qrTimedOut = true;
    setTimeout(() => {
      console.log("QR_TIMEOUT");
      process.exit(1);
    }, 30000);
  });

  client.on("ready", async () => {
    clearTimeout(initTimeout);
    if (qrTimedOut) return;
    try {
      const chats = await client.getChats();
      const communityNameLower = COMMUNITY_NAME.toLowerCase();

      const target = chats.find((c) => {
        if (!c.isGroup) return false;
        const group = c;
        const meta = group.groupMetadata || {};
        const isSubgroup = meta.parentGroupId || meta.parentGroup;
        const nameLower = (c.name || "").toLowerCase();
        const exactMatch = nameLower === communityNameLower;
        const isParentGroup = !isSubgroup;
        return exactMatch || (nameLower.includes(communityNameLower) && isParentGroup);
      });

      if (target) {
        await target.sendMessage(message);
        console.log("MESSAGE_SENT");
      } else {
        console.log("COMMUNITY_NOT_FOUND");
      }
    } catch (err) {
      console.log("SEND_ERROR:" + err.message);
    }
    await client.destroy();
    process.exit(0);
  });

  client.on("auth_failure", (msg) => {
    clearTimeout(initTimeout);
    console.log("AUTH_FAILURE:" + msg);
    process.exit(1);
  });

  client.on("disconnected", (reason) => {
    clearTimeout(initTimeout);
    console.log("SEND_ERROR:Disconnected:" + reason);
    process.exit(1);
  });

  client.initialize();
});
