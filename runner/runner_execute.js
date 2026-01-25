import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const XML_PATH = "../assembler/output/program.xml";

(async () => {
  const xmlText = fs.readFileSync(XML_PATH, "utf-8");

  const browser = await chromium.launch({
    headless: false,
    args: [
      "--mute-audio",
      "--disable-audio-output",
      "--disable-features=AudioServiceSandbox",
      "--disable-features=AudioServiceOutOfProcess"
    ]
  });

  const page = await browser.newPage();

  const localBlocklyPath =
    "file://" + path.resolve("../local_blockly/index.html");

  await page.goto(localBlocklyPath, {
    waitUntil: "domcontentloaded"
  });

  await page.addScriptTag({
    path: path.resolve("./execute_xml.js")
  });

  const result = await page.evaluate(
    xml => window.executeXML(xml),
    xmlText
  );

  fs.mkdirSync("./output", { recursive: true });
  fs.writeFileSync("./output/result.xml", xmlText);
  fs.writeFileSync("./output/result.txt", result.python || "");

  // Let viewer see blocks
  await page.waitForTimeout(5000);

  await browser.close();
})();
