window.executeXML = async function (xmlText) {
  const workspace = Blockly.getMainWorkspace();

  // 1️⃣ Clear canvas
  workspace.clear();

  // 2️⃣ Inject XML
  try {
    const dom = Blockly.utils.xml.textToDom(xmlText);
    Blockly.Xml.domToWorkspace(dom, workspace);
  } catch (e) {
    return {
      status: "xml_error",
      error: String(e)
    };
  }

  // 3️⃣ Generate Python code
  let pythonCode = "";
  try {
    pythonCode = Blockly.Python.workspaceToCode(workspace);
  } catch (e) {
    return {
      status: "python_generation_error",
      error: String(e)
    };
  }

  // 4️⃣ Return result
  return {
    status: "success",
    python: pythonCode
  };
};
