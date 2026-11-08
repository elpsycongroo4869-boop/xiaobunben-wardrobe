import { createHash, webcrypto } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";
import { after, test } from "node:test";
import assert from "node:assert/strict";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const scratch = mkdtempSync(join(tmpdir(), "wardrobe-card-"));
after(() => rmSync(scratch, { recursive: true, force: true }));
const result = JSON.parse(execFileSync(process.env.WARDROBE_PYTHON ?? "python3", [
  "-B", join(root, "scripts/story_start.py"), "prepare",
  "--profile", join(root, "examples/role-existing-gpt-man.json"),
  "--creative-brief", join(root, "examples/brief-man.json"),
  "--pending", join(scratch, "demo"),
], { encoding: "utf-8" }));
const html = readFileSync(result.open_card, "utf-8");
const signed = JSON.parse(readFileSync(result.manifest_path, "utf-8"));
const payload = JSON.parse(html.match(/id="sealed-payload" type="application\/json">([^]*?)<\/script>/u)[1]);
const program = html.match(/<script>([^]*?)<\/script>/u)[1];

async function exercise({ data = payload, denyClipboard = false } = {}) {
  const received = [];
  const elements = {
    "open-box": { disabled: true, addEventListener: (type, handler) => {
      assert.equal(type, "click");
      elements["open-box"].click = handler;
    } },
    "open-status": { textContent: "" },
    "manual-copy": { value: "", hidden: true, focus() {}, select() { this.selected = true; } },
    "sealed-payload": { textContent: JSON.stringify(data) },
  };
  let onDigest;
  const digestDone = new Promise(resolveDigest => { onDigest = resolveDigest; });
  runInNewContext(program, {
    document: { getElementById: name => elements[name] },
    crypto: { subtle: { async digest(...args) {
      const digest = await webcrypto.subtle.digest(...args);
      setImmediate(onDigest);
      return digest;
    } } },
    navigator: { clipboard: { async writeText(value) {
      if (denyClipboard) throw new Error("Clipboard permission denied");
      received.push(value);
    } } },
    TextEncoder,
  });
  await digestDone;
  return { elements, received };
}

test("the verified card copies only on click, byte for byte", async () => {
  const { elements, received } = await exercise();
  assert.equal(elements["open-box"].disabled, false);
  assert.match(html, /<details><summary>创作思路<\/summary>/u);
  assert.equal(received.length, 0);
  await elements["open-box"].click();
  assert.equal(received[0], signed.full_user_message);
  assert.equal(createHash("sha256").update(received[0]).digest("hex"), signed.source_message_sha256);
});

test("denied clipboard keeps the exact message in the manual field", async () => {
  const { elements, received } = await exercise({ denyClipboard: true });
  assert.equal(elements["manual-copy"].hidden, true);
  await elements["open-box"].click();
  assert.equal(elements["manual-copy"].hidden, false);
  assert.equal(elements["manual-copy"].value, signed.full_user_message);
  assert.equal(elements["manual-copy"].selected, true);
  assert.equal(received.length, 0);
});

test("a changed message leaves the opening control disabled", async () => {
  const { elements, received } = await exercise({ data: { ...payload, message: payload.message + "x" } });
  assert.equal(elements["open-box"].disabled, true);
  assert.match(elements["open-status"].textContent, /无法核对/u);
  assert.equal(received.length, 0);
});
