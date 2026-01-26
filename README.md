# Google Blockly Agent: Automated Program Synthesis Pipeline 

Google Blockly Agent is a high-integrity program synthesis engine that converts natural language problem statements into validated Blockly XML and idiomatic Python code. It features a strict 5-phase pipeline ensuring algorithmic correctness and local execution.

## 🎥 Demo Video

👉 [Watch the full pipeline demonstration here](https://drive.google.com/file/d/1k_fExnBmHGbbB1kXQ_jvz8osYrjomXPz/view)


## 📁 Project Structure

```text
├── main.py                 # Core orchestrator and pipeline entry point
├── problems.json           # Batch problem storage (Input data)
├── .env                    # Environment variables (API keys)
├── semantic/               # Module 1: Semantic Planning & Logic
│   ├── planner.py          # LLM orchestration and skeleton filling
│   ├── validator.py        # Static proof of safety and bounds
│   ├── compiler.py         # Plan-to-IR (Block Tree) translation
│   └── schema.py           # Algorithmic Skeletons (Max, Search, Rotate, etc.)
├── assembler/              # Module 2: Block-to-XML Assembly
│   ├── generate_xml.js     # Orchestrates XML production
│   └── xml_builder.js      # Recursive XML tree builder
├── runner/                 # Module 3: Execution & Verification
│   ├── runner_execute.js   # Local headful Playwright runner
│   └── execute_xml.js      # Browser-side Blockly generator
├── local_blockly/          # Local Blockly Environment
│   ├── index.html          # Official Google Blockly playground
│   └── program.xml         # Target XML for visual execution
├── tools/                  # Auxiliary tools (Gmail API integration)
└── outputs/                # Final generated assets per problem
```

## 🚀 Pipeline Flow

The agent follows a deterministic, multi-stage pipeline to ensure zero-hallucination code generation:

### 1. Problem Acquisition & Formalization
- **Fetch**: Integration with **Gmail API** (via `tools/gmail`) pulls incoming problem descriptions and converts them into a structured `problems.json`.
- **Expansion**: The `QuestionExpander` formalizes abstract descriptions into technical algorithm definitions with explicit constraints.

### 2. Semantic Synthesis
- **Planning**: The `SemanticPlanner` classifies the problem by matching it to an **Algorithmic Skeleton** (e.g., `LINEAR_SEARCH`, `FOREACH_AGGREGATE`).
- **Filling**: An LLM fills skeleton slots (placeholders) based on the problem context, with a 3-attempt retry loop for robust JSON output.
- **Validation**: The `CapabilityValidator` performs a static proof, checking for index safety, variable usage, and single-writer invariants.
- **Compilation**: The `SemanticCompiler` translates the plan into a nested **Block Tree** (IR), mapping logic to atomic Blockly actions.

### 3. Visual & Local Execution (official Google Blockly)
- **XML Generation**: `generate_xml.js` builds the Blockly XML and synchronizes it to `local_blockly/program.xml`.
- **Local Runner**: The system opens a **headful Playwright browser** pointing to the local `local_blockly/index.html`.
- **Block Display**: The official Google Blockly environment loads the generated blocks visually for verification.
- **Code Generation**: The runner calls `Blockly.Python.workspaceToCode` locally, ensuring consistent output without relying on external/buggy third-party servers.

### 4. Output Persistence
- After execution, the pipeline organizes results into the `outputs/` directory.
- Folders are named `Problem_PID` (e.g., `Problem_PID-1008`).
- Each folder contains:
    - `{TEAM_ID}_TL_{PID}.xml`: Validated Blockly source.
    - `{TEAM_ID}_TL_{PID}.txt`: Final idiomatic Python solution.
    - `{TEAM_ID}_TL_{PID}_bug.txt`: Validation/Debug logs.

## 🛠 Setup

1. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Node.js Dependencies**:
   ```bash
   npm install
   ```
3. **Environment**:
   Create a `.env` file with your `OPENROUTER_API_KEY`.

## 🖥 Usage

Run the full batch pipeline:
```bash
python main.py
```

Run in test mode for a single logic check:
```bash
python main.py --test
```
