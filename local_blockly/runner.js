// Define 'math_to_int' block
Blockly.Blocks['math_to_int'] = {
  init: function () {
    this.appendValueInput("VALUE")
      .setCheck(null);
    this.setOutput(true, "Number");
    this.setColour(230);
    this.setTooltip("Converts text to integer");
  }
};

// Define 'math_to_int' generator
Blockly.Python.forBlock['math_to_int'] = function (block) {
  var value = Blockly.Python.valueToCode(block, 'VALUE', Blockly.Python.ORDER_NONE) || '0';
  return ['int(' + value + ')', Blockly.Python.ORDER_FUNCTION_CALL];
};

// Create workspace
const workspace = Blockly.inject("blocklyDiv", {
  toolbox: `<xml></xml>` // empty toolbox (we load XML directly)
});

// Load XML from file
async function loadAndRun() {
  const response = await fetch("./program.xml");
  const xmlText = await response.text();

  const dom = Blockly.utils.xml.textToDom(xmlText);
  Blockly.Xml.domToWorkspace(dom, workspace);

  // Generate Python code
  const pythonCode = Blockly.Python.workspaceToCode(workspace);

  console.log("===== GENERATED PYTHON =====");
  console.log(pythonCode);
  console.log("============================");

  // Optional: expose globally
  window.generatedPython = pythonCode;
}

loadAndRun();
