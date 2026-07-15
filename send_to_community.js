const { Client, LocalAuth } = require("whatsapp-web.js");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

require("dotenv").config();

const sessionDir = path.resolve(__dirname, ".wwebjs_auth", "session-dc_news_bot");
["SingletonLock", "SingletonSocket", "first_party_sets.db-journal"].forEach((f) => {
  try { fs.unlinkSync(path.join(sessionDir, f)); } catch (_) {}
});

function killChrome() {
  try { execSync("taskkill /f /im chrome.exe 2>nul", { stdio: "ignore" }); } catch (_) {}
  try { execSync("taskkill /f /im chromium.exe 2>nul", { stdio: "ignore" }); } catch (_) {}
}

function resultJson(obj) {
  const line = "RESULT:" + JSON.stringify(obj);
  process.stdout.write(line + "\n", () => process.exit(obj.status === "sent" ? 0 : 1));
}

let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", async () => {
  const payload = JSON.parse(input);
  const chatId = payload.chat_id || "";
  const message = payload.message || "";

  if (!message) { resultJson({ status: "error", error: "Empty message" }); return; }
  if (!chatId) { resultJson({ status: "error", error: "No chat_id provided" }); return; }

  const puppeteerOpts = {
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-features=FirstPartySets", "--disable-blink-features=AutomationControlled"],
  };
  const chromePath = process.env.CHROME_PATH;
  if (chromePath) puppeteerOpts.executablePath = chromePath;

  async function trySend() {
    const client = new Client({
      authStrategy: new LocalAuth({ clientId: "dc_news_bot", rmMaxRetries: 10 }),
      puppeteer: puppeteerOpts,
    });

    let initTimeout = setTimeout(() => {
      resultJson({ status: "error", error: "Initialization timed out after 90s" });
    }, 90000);

    let qrTimedOut = false;
    client.on("qr", () => {
      console.log("QR_CODE_REQUIRED");
      qrTimedOut = true;
      setTimeout(() => { resultJson({ status: "error", error: "QR_TIMEOUT" }); }, 30000);
    });

    client.on("ready", async () => {
      clearTimeout(initTimeout);
      if (qrTimedOut) return;

      try {
        const sent = await client.sendMessage(chatId, message);

        // sendMessage may return undefined if getMessageModel fails
        // inside the library, but the message was still sent by
        // WhatsApp Web. Treat any non-thrown call as success.
        if (sent && sent.fromMe && sent.id && sent.id._serialized) {
          resultJson({
            status: "sent",
            chat_id: chatId,
            message_id: sent.id._serialized,
            ack: typeof sent.ack === "number" ? sent.ack : 1,
          });
        } else {
          // Message went through but library post-processing failed.
          // Report success without message_id.
          resultJson({
            status: "sent",
            chat_id: chatId,
            message_id: null,
            ack: -1,
          });
        }
      } catch (err) {
        resultJson({ status: "error", error: err.message || String(err), chat_id: chatId });
      }

      try { await client.destroy(); } catch (_) {}
    });

    client.on("auth_failure", (msg) => {
      clearTimeout(initTimeout);
      resultJson({ status: "error", error: "AUTH_FAILURE:" + msg });
    });

    client.on("disconnected", (reason) => {
      clearTimeout(initTimeout);
      resultJson({ status: "error", error: "Disconnected:" + reason });
    });

    try {
      await client.initialize();
    } catch (err) {
      clearTimeout(initTimeout);
      throw err;
    }
  }

  for (let i = 1; i <= 3; i++) {
    killChrome();
    try {
      await trySend();
      return;
    } catch (err) {
      if (i < 3) {
        console.error("RETRY_LOG:Attempt " + i + " failed: " + err.message);
        await new Promise((r) => setTimeout(r, 3000));
      } else {
        resultJson({ status: "error", error: "All 3 attempts failed: " + err.message });
      }
    }
  }
});
