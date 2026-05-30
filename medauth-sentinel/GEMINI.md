# MedAuth Sentinel: Foundational Mandates

This document serves as the primary source of truth for architecture, conventions, and workflows for MedAuth Sentinel. All development must adhere to these standards.

## 1. Architectural Principles

### 1.1 Three-Agent Pipeline
The system operates as an autonomous pipeline consisting of three distinct agents:
1. **IntakeAgent:** Validates request structure and data integrity.
2. **DecisionAgent:** Analyzes patient history and payer policies to reach a decision (APPROVE/DENY).
3. **CriticAgent:** Performs adversarial review of the DecisionAgent's output.

### 1.2 Self-Correction Loop
If the `CriticAgent` disagrees with the `DecisionAgent` (with severity 'minor' or 'major'), the `DecisionAgent` MUST be re-invoked with the critic's feedback. This loop is managed by `backend/orchestrator.py`.

### 1.3 Tool-Based Data Access
Agents MUST NOT access data files directly. All data retrieval (patients, medications, policies) MUST go through the tools layer in `backend/tools/`. This ensures the system can be easily migrated to a database or FHIR API in the future.

---

## 2. Project Conventions

### 2.1 Backend (FastAPI)
- **Models:** All API request/response structures MUST be defined in `backend/models.py` using Pydantic.
- **Endpoints:** Main logic should be kept in `orchestrator.py` or agent files; `main.py` should primarily handle routing and HTTP-level logic.
- **Async:** Prefer async endpoints in `main.py` where appropriate, though the agent orchestrator is currently synchronous.

### 2.2 Frontend (Astro + React Islands)
- **Architecture:** The frontend is an Astro application using a Multi-Page Architecture (MPA) with React islands for interactive components.
- **State Management:** Shared state (like authorization results) is managed via `nanostores` with persistence to ensure data survives navigation.
- **Styling:** Uses Tailwind CSS 4 with a "Advanced Diagnostics" dark-mode aesthetic.
- **Routing:** Managed by Astro's file-based routing (`src/pages/`) with `<ViewTransitions />` for smooth transitions.
- **Configuration:** API settings are managed in `frontend/src/config.js`, supporting both `PUBLIC_` and `VITE_` environment variables.

### 2.3 Prompt Management
- **YAML Files:** Agent system prompts MUST be stored in `prompts/*.yaml`. Never hardcode prompts in Python code.
- **Structure:** Prompts should follow the format defined in `backend/models.py` (e.g., `agent_name`, `system_prompt`, `version`).

### 2.4 Data Layer
- **JSON Persistence:** Data is stored in `data/*.json`.
- **Generation:** Synthetic data is generated via `backend/generate_data.py`. This script is automatically triggered by the FastAPI `lifespan` hook if data files are missing.

---

## 3. Development Workflows

### 3.1 Adding a New Agent
1. Create the agent class in `backend/agents/`.
2. Create the corresponding system prompt in `prompts/`.
3. Update `backend/orchestrator.py` to integrate the agent into the pipeline.
4. Add a Pydantic model in `backend/models.py` if new response structures are needed.

### 3.2 Testing
- **Unit Tests:** Use `pytest` for testing individual tools in `backend/tools/`.
- **Integration Tests:** Test the full orchestrator flow in `tests/test_orchestrator.py`.
- **API Tests:** Use `.http` files (VS Code REST Client) for quick manual endpoint verification.
- **Mandate:** Every new feature or bug fix MUST be accompanied by a test case.

### 3.3 Security
- **API Keys:** NEVER commit `.env` files or hardcode the `GROQ_API_KEY`. Use `.env.example` as a template.
- **Validation:** Always use Pydantic for input validation to prevent injection or malformed data issues.

---

## 4. Agent Operational Guidance

When working on this project, prioritize:
1. **Traceability:** Ensure every agent step is captured in the `trace` object returned by the orchestrator.
2. **Transparency:** Maintain clear reasoning in agent outputs so the "Thinking Process" can be visualized in the UI.
3. **Idiomatic Python:** Follow PEP 8 and use type hints where possible.
4. **Component Reusability:** In the frontend, extract common UI patterns (like the agent trace view) into reusable components.
