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
        const sentResult = await client.pupPage.evaluate(async (cid, msgText) => {
          const WidFactory = window.require("WAWebWidFactory");
          const ChatColl = window.require("WAWebCollections").Chat;
          const MsgKey = window.require("WAWebMsgKey");
          const UserPrefs = window.require("WAWebUserPrefsMeUser");
          const Ephemeral = window.require("WAWebGetEphemeralFieldsMsgActionsUtils");
          const SendAction = window.require("WAWebSendMsgChatAction");
          const MsgColl = window.require("WAWebCollections").Msg;

          const wid = WidFactory.createWid(cid);
          const chat = ChatColl.get(wid);
          if (!chat) return { status: "not_found", error: "Chat not found for " + cid };

          const newId = await MsgKey.newId();
          const lidUser = UserPrefs.getMaybeMeLidUser();
          const meUser = UserPrefs.getMaybeMePnUser();
          let from = chat.id.isLid() ? lidUser : meUser;
          let participant;

          if (typeof chat.id?.isGroup === "function" && chat.id.isGroup()) {
            from = chat.groupMetadata && chat.groupMetadata.isLidAddressingMode ? lidUser : meUser;
            participant = WidFactory.asUserWidOrThrow(from);
          }

          const newMsgKey = new MsgKey({ from, to: chat.id, id: newId, participant, selfDir: "out" });
          const eph = Ephemeral.getEphemeralFields(chat);

          const msg = {
            id: newMsgKey,
            ack: 0,
            body: msgText,
            from: from,
            to: chat.id,
            local: true,
            self: "out",
            t: parseInt(Date.now() / 1000),
            isNewMsg: true,
            type: "chat",
            ...eph,
          };

          const [msgPromise, resultPromise] = SendAction.addAndSendMsgToChat(chat, msg);
          await msgPromise;
          const sendResult = await resultPromise;

          // Try to get the sent message ID from the collection
          let msgId = null;
          try {
            const sentMsg = MsgColl.get(newMsgKey._serialized);
            if (sentMsg && sentMsg.id) msgId = sentMsg.id._serialized;
          } catch (_) {}

          return {
            status: sendResult && sendResult.messageSendResult === "OK" ? "sent" : "error",
            messageSendResult: sendResult ? sendResult.messageSendResult : "UNKNOWN",
            chat_id: cid,
            message_id: msgId,
            ack: msgId ? 1 : -1,
            t: sendResult ? sendResult.t : null,
          };
        }, chatId, message);

        if (sentResult.status === "sent") {
          resultJson(sentResult);
        } else {
          resultJson(sentResult);
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
