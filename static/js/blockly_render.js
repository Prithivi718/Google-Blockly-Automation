/**
 * blockly_render.js — Google Blockly Agent UI
 * 
 * Handles Blockly injection, XML loading, and Python generation.
 * Relies on Blockly being loaded via CDN in output.html.
 */

(function() {
    console.log("blockly_render.js loaded - V2");
    let workspace = null;

    // ── Custom Block Definitions (Loaded from local_blockly/runner.js) ── //
    Blockly.Blocks['math_to_int'] = {
        init: function () {
            this.appendValueInput("VALUE").setCheck(null);
            this.setOutput(true, "Number");
            this.setColour(230);
            this.setTooltip("Converts text to integer");
        }
    };

    Blockly.Blocks['lists_append'] = {
        init: function() {
            this.appendValueInput("LIST").setCheck("Array").appendField("append to list");
            this.appendValueInput("ITEM").setCheck(null).appendField("item");
            this.setPreviousStatement(true, null);
            this.setNextStatement(true, null);
            this.setColour(260);
            this.setTooltip("Appends an item to a list");
        }
    };

    Blockly.Blocks['controls_return'] = {
        init: function() {
            this.appendValueInput("VALUE").setCheck(null).appendField("return");
            this.setPreviousStatement(true, null);
            this.setNextStatement(false, null);
            this.setColour(210);
            this.setTooltip("Exits a function with a value");
        }
    };

    Blockly.Blocks['math_minmax'] = {
        init: function() {
            this.appendDummyInput().appendField(new Blockly.FieldDropdown([["min", "MIN"], ["max", "MAX"]]), "OP");
            this.appendValueInput("A").setCheck("Number");
            this.appendValueInput("B").setCheck("Number");
            this.setOutput(true, "Number");
            this.setColour(230);
            this.setTooltip("Returns min/max of two numbers");
        }
    };

    Blockly.Blocks['controls_repeat_while'] = {
        init: function() {
            this.appendValueInput("BOOL").setCheck("Boolean").appendField("repeat");
            this.appendDummyInput().appendField(new Blockly.FieldDropdown([["while", "WHILE"], ["until", "UNTIL"]]), "MODE");
            this.appendStatementInput("DO").appendField("do");
            this.setPreviousStatement(true, null);
            this.setNextStatement(true, null);
            this.setColour(120);
            this.setTooltip("Repeat while/until a condition is met");
        }
    };

    Blockly.Blocks['text_to_string'] = {
        init: function() {
            this.appendValueInput("VALUE").setCheck(null).appendField("to string");
            this.setOutput(true, "String");
            this.setColour(160);
            this.setTooltip("Converts value to string");
        }
    };

    Blockly.Blocks['text_to_number'] = {
        init: function() {
            this.appendValueInput("TEXT").setCheck("String").appendField("to number");
            this.setOutput(true, "Number");
            this.setColour(230);
            this.setTooltip("Converts string to number");
        }
    };

    console.log("Custom blocks registered: math_to_int, lists_append, controls_return, etc.");

    // Delay Python generator definition until generatePython is called, or define safely here
    // Wait for Blockly.Python to be available. Since Blockly CDN loads immediately, it should be available.
    if (typeof Blockly.Python !== 'undefined') {
        Blockly.Python.forBlock['math_to_int'] = function (block) {
            var value = Blockly.Python.valueToCode(block, 'VALUE', Blockly.Python.ORDER_NONE) || '0';
            return ['int(' + value + ')', Blockly.Python.ORDER_FUNCTION_CALL];
        };

        Blockly.Python.forBlock['lists_append'] = function(block) {
            var list = Blockly.Python.valueToCode(block, 'LIST', Blockly.Python.ORDER_NONE) || '[]';
            var item = Blockly.Python.valueToCode(block, 'ITEM', Blockly.Python.ORDER_NONE) || 'None';
            return list + '.append(' + item + ')\n';
        };

        Blockly.Python.forBlock['controls_return'] = function(block) {
            var val = Blockly.Python.valueToCode(block, 'VALUE', Blockly.Python.ORDER_NONE) || 'None';
            return 'return ' + val + '\n';
        };

        Blockly.Python.forBlock['math_minmax'] = function(block) {
            var op = block.getFieldValue('OP') === 'MIN' ? 'min' : 'max';
            var valA = Blockly.Python.valueToCode(block, 'A', Blockly.Python.ORDER_NONE) || '0';
            var valB = Blockly.Python.valueToCode(block, 'B', Blockly.Python.ORDER_NONE) || '0';
            return [op + '(' + valA + ', ' + valB + ')', Blockly.Python.ORDER_FUNCTION_CALL];
        };

        Blockly.Python.forBlock['controls_repeat_while'] = function(block) {
            var mode = block.getFieldValue('MODE');
            var cond = Blockly.Python.valueToCode(block, 'BOOL', 
                mode == 'WHILE' ? Blockly.Python.ORDER_NONE : Blockly.Python.ORDER_LOGICAL_NOT) || 'False';
            var branch = Blockly.Python.statementToCode(block, 'DO') || '  pass\n';
            if (mode == 'UNTIL') {
                cond = 'not ' + cond;
            }
            return 'while ' + cond + ':\n' + branch;
        };

        Blockly.Python.forBlock['text_to_string'] = function(block) {
            var val = Blockly.Python.valueToCode(block, 'VALUE', Blockly.Python.ORDER_NONE) || "''";
            return ['str(' + val + ')', Blockly.Python.ORDER_FUNCTION_CALL];
        };

        Blockly.Python.forBlock['text_to_number'] = function(block) {
            var val = Blockly.Python.valueToCode(block, 'TEXT', Blockly.Python.ORDER_NONE) || "'0'";
            return ['float(' + val + ')', Blockly.Python.ORDER_FUNCTION_CALL];
        };
    }

    /**
     * Injects Blockly into the specified container and loads XML.
     * @param {string} xmlString - The Blockly XML string.
     */
    window.renderBlockly = function(xmlString) {
        const container = document.getElementById('blockly-div');
        if (!container) return;

        // Clean XML: Fix hallucinations from LLM Fallback (e.g., 'controls_flow' -> 'controls_flow_statements')
        if (xmlString) {
            xmlString = xmlString.replace(/type="controls_flow"/g, 'type="controls_flow_statements"');
        }

        // Clean up previous workspace if it exists
        if (workspace) {
            workspace.dispose();
        }

        // Define a minimal theme or use default
        // We use a dark-ish theme to match the UI
        workspace = Blockly.inject('blockly-div', {
            readOnly: false,
            toolbox: '<xml></xml>',
            trashcan: true,
            scrollbars: true,
            spacing: 20,
            zoom: {
                controls: true,
                wheel: true,
                startScale: 1.0,
                maxScale: 3,
                minScale: 0.3,
                scaleSpeed: 1.2
            },
            theme: Blockly.Themes.Classic // Modern Blockly comes with themes
        });

        // Add change listener for real-time Python generation
        workspace.addChangeListener(function(event) {
            // Only trigger on actual workspace modifications (skip UI/Selection events)
            if (event.type == Blockly.Events.BLOCK_MOVE ||
                event.type == Blockly.Events.BLOCK_CHANGE ||
                event.type == Blockly.Events.BLOCK_DELETE ||
                event.type == Blockly.Events.BLOCK_CREATE) {
                
                if (typeof window.onBlocklyWorkspaceChanged === 'function') {
                    window.onBlocklyWorkspaceChanged();
                }
            }
        });

        try {
            const xml = Blockly.utils.xml.textToDom(xmlString);
            Blockly.Xml.domToWorkspace(xml, workspace);
            
            // Adjust the view to center the blocks
            workspace.scrollCenter();
        } catch (e) {
            console.error("Failed to load XML into Blockly:", e);
            container.innerHTML = `<div style="padding: 2rem; color: var(--danger);">Error rendering blocks: ${e.message}</div>`;
        }
    };

    /**
     * Generates Python code from the current workspace.
     * @returns {string} The generated Python code.
     */
    window.generatePython = function() {
        if (!workspace) return "# Error: No workspace";
        
        // Ensure Python generator is loaded
        if (!Blockly.Python) {
            return "# Error: Blockly Python generator not loaded";
        }

        try {
            return Blockly.Python.workspaceToCode(workspace);
        } catch (e) {
            console.error("Failed to generate Python:", e);
            return `# Error generating Python: ${e.message}`;
        }
    };

    /**
     * Toggles read-only mode (useful for "Advanced" mode)
     * @param {boolean} editable 
     */
    window.setBlocklyEditable = function(editable) {
        if (!workspace) return;
        workspace.options.readOnly = !editable;
        // Re-injecting is usually cleaner for significant option changes in Blockly
    };

})();
