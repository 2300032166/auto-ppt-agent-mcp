# Auto-PPT Agent (MCP + Hugging Face)

A production-ready AI agent that generates complete, themed PowerPoint presentations based on a single topic input using the **Model Context Protocol (MCP)** and **Hugging Face Transformers**.

The agent operates in an autonomous loop: it plans your slide titles, searches for real factual data from the web, and delegates the PowerPoint rendering and formatting to dedicated MCP servers.

## 🌟 Key Features
- **MCP-Powered Architecture**: Uses `fastmcp` to expose a PowerPoint Builder (`ppt_server.py`) and a Web Search tool (`web_search_server.py`) as completely decoupled MCP servers.
- **Real-Time Web Search**: Retrieves factual data from the web using DuckDuckGo. This guarantees the bullet points contain real facts rather than LLM hallucinations.
- **Agentic Planning**: A localized LLM (`google/flan-t5-base`) acts strictly as a planner to divide your topic into slide titles and delegates execution to the tools.
- **Advanced Theme Engine**: Supports rich, dynamic themes (`professional`, `dark`, `academic`, `creative`, `minimal`). Themes can be hardcoded via CLI arguments or automatically inferred from your topic description.
- **Defense-In-Depth Formatting**: Clean, professional layout and auto-sanitized content so text displays perfectly without weird LLM generation artifacts.

---

## 🛠️ Setup Instructions

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
Install all required packages using pip:
```bash
pip install -r requirements.txt
```

### 3. Model Download
The first time you launch the agent, it will download the `google/flan-t5-base` model. This requires approximately 1GB of disk space and a working internet connection.

---

## 🚀 Running the Project: 2 Ways

You can run this project either as a fully standalone autonomous agent, or by directly integrating the built-in MCP servers into your favorite GenAI MCP Client (e.g. Claude Desktop, Cursor).

### Way 1: Fully Autonomous Agent (Recommended)
This runs the main python script which automatically wires up the LLM, the Theme Engine, the Web Search MCP tool, and the PPT Builder MCP tool to generate everything end-to-end.

**Sample Commands:**
```bash
# Basic usage with inline topic
python run_agent.py "Artificial Intelligence in Healthcare"

# Explicitly defining a theme (professional, dark, academic, creative, minimal)
python run_agent.py "Space Exploration" --theme dark

# Customizing the output filename and slide count
python run_agent.py "History of Rome" --slides 10 --output rome_history.pptx

# Interactive mode (will prompt you for a topic)
python run_agent.py
```
> The final `.pptx` file will be saved in the `output/` directory!

### Way 2: Direct MCP Server Integration (MCP Client / Inspector)
Because the PPT Builder and Search tools are decoupled standard MCP servers, any MCP capable client ( MCP Inspector) can connect to them.



**Testing via MCP Inspector:**
If you wish to test the server endpoints directly in your browser:
```bash
npx @modelcontextprotocol/inspector python ppt_server.py
```

---

## 🏗️ Project Structure
- `agent/`: Contains the LLM planning logic, agentic execution loop, and Hugging Face integration.
- `mcp_servers/`: Houses the standalone MCP server files (`ppt_server.py` and `web_search_server.py`).
- `themes/`: Theme configurations (`ThemeConfig`) and color/font parsing utilities.
- `config/`: Centralized settings (number of slides, directories, models).
- `utils/`: Search extraction text-cleaning tools and common helper scripts.
- `output/`: Folder where the generated `.pptx` files reside.
- `run_agent.py`: The main entry script to start the autonomous flow.

---

## 📊 Logging & Output
When running autonomously, the console will stream:
- `Planning slides...` → T5 LLM formulates presentation structure.
- `set_theme()...` → Identifies styling tokens.
- `mcp search_web(...)` → Queries DDGS for factual data points.
- `mcp write_text(...)` → Pushes parsed data into slide templates.
- `mcp save_presentation(...)` → Creates the final PPTX.
