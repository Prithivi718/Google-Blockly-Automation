import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { buildBlockXML } from "./xml_builder.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Input from Python compiler
// Resolves to: assembler/../semantic/output/block_tree.json
const blockTreePath = path.join(__dirname, "../semantic/output/block_tree.json");

console.log(`Reading block tree from: ${blockTreePath}`);

if (!fs.existsSync(blockTreePath)) {
  console.error(`Error: File not found at ${blockTreePath}`);
  process.exit(1);
}

const blockTree = JSON.parse(
  fs.readFileSync(blockTreePath, "utf-8")
);

// Build XML body
const xmlBody = buildBlockXML(blockTree);

// Wrap with Blockly root
const finalXML = `
<xml xmlns="https://developers.google.com/blockly/xml">
${xmlBody}
</xml>
`.trim();

// Write output
// Write output
const outputPath = path.join(__dirname, "output");
fs.mkdirSync(outputPath, { recursive: true });
fs.writeFileSync(path.join(outputPath, "program.xml"), finalXML, "utf-8");

// Copy to local_blockly for visual execution
const blocklyPath = path.join(__dirname, "../local_blockly/program.xml");
fs.writeFileSync(blocklyPath, finalXML, "utf-8");

console.log(`✅ XML generated: ${path.join(outputPath, "program.xml")}`);
