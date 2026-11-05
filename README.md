# 🎸 Empório da Música — Intelligent Customer Support Agent

> Text-based conversational agent prototype engineered for the **Artefact AI Engineer – Full-Stack for Generative AI Applications** technical assessment.

This project delivers an end-to-end conversational AI solution for **Empório da Música**, a traditional musical instrument store based in Campo Grande/MS, Brazil. The agent automates customer service operations by dynamically routing between deterministic transactional queries (product availability, live prices, orders, and promotions) and unstructured policy retrieval (returns, warranties, shipping, and business hours), while strictly enforcing domain guardrails.

---

## 🏛️ System Architecture & Decision Flow

The solution follows a modular, framework-agnostic design powered by **Native Function Calling**, ensuring deterministic execution, minimal latency, and zero data leakage:
code
Code
┌───────────────────────────────┐
              │       Customer Message        │
              └───────────────┬───────────────┘
                              │
                              ▼
  ┌──────────────────────────────────────────────────────┐
  │  Full-Stack UI Layer: Terminal CLI & Streamlit App   │
  └───────────────────────────┬──────────────────────────┘
                              │
                              ▼
  ┌──────────────────────────────────────────────────────┐
  │  Agent Core: Google Gemini + Rolling Memory Buffer    │
  └───────────────────────────┬──────────────────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
     ▼                        ▼                        ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Catalog Tool │ │ Order Tool │ │ Policy Tool │
│ (SQLite / Pandas)│ │ (SQLite Joins) │ │ (Semantic RAG) │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
│ │ │
▼ ▼ ▼
Products & Promotions Orders & Tracking Policies & Legal CDC
(Deterministic Match) (Relational Integrity) (Chunk-based Retrieval)
code
Code
---

## ⚙️ Technical Decisions & Trade-Off Analysis

### 1. LLM Provider & Model Choice
* **Decision:** **Google Gemini ( `gemini-3.8-flash`)**  Google AI Studio.
* **Rationale:** High precision in schema extraction and argument binding, millisecond-level time-to-first-token (TTFT), low cost, and reproducible evaluation via API key.

### 2. Framework Approach: Native SDK vs. Heavy Abstractions
* **Decision:** **Modular Native Tool Calling** over traditional LangChain/LlamaIndex monoliths.
* **Rationale:** Avoids leaky abstractions and bloat; ensures full observability over payloads and demonstrates mastery of core GenAI primitives.

### 3. Structured Data Strategy: In-Memory SQLite vs. Prompt Injection
* **Decision:** Ingesting operational CSVs (`products`, `categories`, `orders`, `order_items`, `customers`, `promotions`) into an **in-memory SQLite database (`:memory:`)**.
* **Rationale:** Passing raw CSVs into LLM prompts leads to arithmetic hallucinations and broken price range filters. SQL execution guarantees deterministic calculations and exact joins.

### 4. Unstructured Knowledge Base: Topical Section RAG
* **Decision:** Segmenting the 8-page internal policy manual (`políticas_da_loja.pdf`) into discrete topical sections rather than naive fixed token windows.
* **Rationale:** Preserves regulatory coherence across critical policies (7-day CDC online return rules vs. 30-day manufacturing defect warranties).

### 5. Temporal Alignment (Handling Time Drift)
* **Decision:** Explicit simulation anchor using `REFERENCE_DATE=2026-03-23`.
* **Rationale:** Prevents time-drift assertion errors when evaluating 7-day CDC return eligibility against dataset orders dated late 2025/early 2026.

---

## 🛡️ Business Rules & Guardrails Implementation

1. **Strict Negative Scope (No Accessories):** Exclusively retails complete musical instruments. Inquiries regarding strings, picks, cables, pedals, cases, straps, or amplifiers are politely rejected and redirected to local partners.
2. **Promotions & Non-Cumulative PIX Discount:** A 5% discount is applied for upfront PIX payments on standard catalog items. Strictly non-cumulative with items with active promotions in `promotions.csv`. Inactive promotions (`is_active = 0`) are transparently communicated as expired.
3. **Inventory & Lifecycle States:** Stock=0 alerts of temporary unavailability and recommends alternatives; status='discontinued' alerts of end-of-life models.
4. **Consumer Protection Code (CDC):** 7-day unconditional withdrawal for online purchases (freight paid by store). Sanitary exception: wind instrument mouthpieces are strictly ineligible for exchange.
5. **Regional Delivery Policies (Campo Grande):** Local metropolitan deliveries: Free for orders over R$ 500.00; fixed fee of R$ 35.00 below that threshold (1–3 business days delivery via motoboy).

---

## 💬 Verified Interaction Logs (Test Scenarios)

* **Scenario 1 (Price Filter <= R$ 1000):** Customer asked for guitars under R$ 1,000. Agent queried SQLite and listed 10 matching models in ascending price order (Tagima Memphis R$ 429.90 up to Yamaha C70 R$ 849.00) with PIX values.
* **Scenario 2 (Store Info & Hours):** Customer asked for address and schedule. Agent retrieved policy and provided Rua 14 de Maio, 3200 — Centro, Mon–Fri 09:00–18:00, Sat 09:00–13:00.
* **Scenario 3 (Expired Promotion vs. PIX):** Customer asked for expired Takamine GD20 12% discount. Agent clarified campaign had ended, quoted table price (R$ 2,199.00), applied 5% PIX (R$ 2,089.05), and explained non-cumulativity.
* **Scenario 4 (Online Return Eligibility):** Customer asked to return online order after 4 days. Agent confirmed eligibility under 7-day CDC rule, confirmed store pays return freight, and requested order ID.
* **Scenario 5 (Negative Scope / Accessories):** Customer asked for guitar strings and picks. Agent politely refused, stating Empório da Música sells instruments only, suggesting downtown partner shops.

---

## 🚀 Setup & Execution Guide

```bash
# 1. Clone repository
git clone https://github.com/PriCas/DesafioArtefactAgenteAtendimentoEmporioMusica.git
cd DesafioArtefactAgenteAtendimentoEmporioMusica

# 2. Virtual environment setup
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell

Linux / macOS or Git Bash:
python -m venv venv
source venv/Scripts/activate  # or source venv/bin/activate on Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env

# 5. Run Terminal CLI
python main.py

# 6. Run Streamlit Web Interface
streamlit run app.py
🔮 Known Limitations & Production Roadmap
Two-Factor Authentication for Customer Data (LGPD): Enforce identity verification (phone/CPF via SMS OTP) before exposing order details and addresses.
Hybrid Semantic Search: Integrate a lightweight vector store (Qdrant or ChromaDB) paired with dense embeddings (all-MiniLM-L6-v2).
Automated Human Escalation: Real-time sentiment analysis to transfer frustrated users to human agents via Zendesk or WhatsApp API.
🤖 AI Code Assistants & Engineering Workflow
AI assistants (Claude 3.7 Sonnet and ChatGPT) were actively utilized throughout development for:
Scaffolding & SQL Modeling: Generating in-memory SQLite schema definitions and tool typing decorators.
Adversarial Prompt Hardening: Simulating boundary-breaking prompts to refine the negative-catalog guardrail.
Documentation & Translation: Structuring this technical defense in alignment with international data consultancy standards.