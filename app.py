"""
PARADOX ENGINE — Autonomous Chaos Reasoning Platform (Hackathon Edition)
--------------------------------------------------------------------------
"Find What Your System Was Never Designed For."

This is a deliberately simplified rebuild of the original PRD's architecture,
scoped down so it can be built, run, and deployed the exact same way as our
first project: VS Code -> GitHub -> Streamlit Cloud.

Simplified from the original pitch:
  - React/Vite/Tailwind/ReactFlow frontend     -> single-file Streamlit app
  - FastAPI backend                             -> plain Python functions
  - LangGraph / LangChain orchestration         -> plain Python function calls
  - Groq / Llama-3.3-70B                        -> Claude API (Anthropic)
  - ChromaDB + FastEmbed vector RAG             -> small curated pattern
                                                    library + keyword retrieval
  - React Flow DAG visualization                -> Streamlit's graphviz_chart
  - Arbitrary system ingestion                  -> one fixed, fully-built
                                                    scenario (as the original
                                                    PRD itself recommended for
                                                    the hackathon MVP)

What's kept faithful to the original idea:
  - 5 distinct specialist AI agents (System Analyst, Assumption Hunter,
    Paradox Generator, Failure Analyst, Recovery Agent)
  - "AI reasons, code verifies" — the failure simulation is 100% deterministic
    Python, never guessed by the AI
  - The full Discover -> Break -> Simulate -> Recover -> Re-Test loop
  - The Counterfactual Lab and the Cascade Map
  - A downloadable "Reality Forge" JSON reproduction file

Run with:  streamlit run paradox_app.py
Requires:  pip install streamlit anthropic graphviz
Requires:  ANTHROPIC_API_KEY environment variable
"""

import os
import re
import json
from datetime import datetime

import streamlit as st

try:
    import anthropic
except ImportError:
    anthropic = None


# =========================================================
# 1. PAGE CONFIG + THEME
# =========================================================

st.set_page_config(
    page_title="Paradox Engine — Autonomous Chaos Reasoning",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

    html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; }

    /* TERMINAL / CONSOLE THEME — deliberately distinct from any card-dashboard look */
    .stApp {
        background-color: #06080D !important;
        background-image:
            linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
        background-size: 28px 28px;
    }
    .main, .block-container { background-color: transparent !important; }
    .stApp, .stApp p, .stApp span, .stApp label, .stApp div, .stMarkdown, .stMarkdown p {
        color: #B7C4D1 !important;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #EAF0F5 !important;
    }

    /* Terminal-style header, no rounded card look */
    .pe-header {
        background: #0A0E17;
        border: 1px solid #1E2A1E;
        border-left: 3px solid #39FF6A;
        padding: 22px 28px;
        margin-bottom: 22px;
        font-family: 'JetBrains Mono', monospace;
    }
    .pe-header h1 {
        margin: 0;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 28px;
        font-weight: 700;
        color: #EAF0F5 !important;
        letter-spacing: -0.3px;
    }
    .pe-header p {
        margin: 10px 0 0 0;
        font-size: 13.5px;
        color: #7C8CA0 !important;
    }
    .pe-tag {
        display: inline-block;
        color: #39FF6A !important;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    .pe-tag::before { content: "[ "; }
    .pe-tag::after { content: " ]"; }

    /* Readout panels — flat, left-border accent only, NO rounded corners,
       NO hover state, so they never look clickable when they aren't */
    .pe-panel {
        background: #0A0E17;
        border: 1px solid #1A2130;
        border-left: 3px solid #3A4A5C;
        padding: 16px 18px;
        margin-bottom: 12px;
        font-size: 13.5px;
    }
    .pe-panel-risk-high { border-left-color: #FF4D4D; }
    .pe-panel-risk-medium { border-left-color: #F5C542; }
    .pe-panel-risk-low { border-left-color: #4FA8E0; }

    .pe-tagchip {
        display: inline-block;
        padding: 2px 9px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.5px;
        border: 1px solid;
    }
    .pe-tagchip-high { color: #FF4D4D !important; border-color: #FF4D4D; }
    .pe-tagchip-medium { color: #F5C542 !important; border-color: #F5C542; }
    .pe-tagchip-low { color: #4FA8E0 !important; border-color: #4FA8E0; }
    .pe-tagchip-good { color: #39FF6A !important; border-color: #39FF6A; }
    .pe-tagchip-bad { color: #FF4D4D !important; border-color: #FF4D4D; }
    .pe-tagchip-neutral { color: #8A97AC !important; border-color: #4A5568; }

    .pe-mono {
        font-family: 'JetBrains Mono', monospace;
        background: #050709;
        border: 1px solid #1A2130;
        padding: 12px 14px;
        font-size: 12.5px;
        color: #8FD9A8 !important;
        white-space: pre-wrap;
        line-height: 1.6;
    }

    .pe-section-title {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 16px;
        font-weight: 700;
        color: #EAF0F5 !important;
        margin: 20px 0 10px 0;
        padding-bottom: 6px;
        border-bottom: 1px dashed #26304A;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .pe-section-title::before { content: "// "; color: #39FF6A; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #050709 !important;
        border-right: 1px solid #141A26;
    }
    section[data-testid="stSidebar"] * { color: #9AAAC0 !important; font-family: 'JetBrains Mono', monospace; }
    section[data-testid="stSidebar"] label { color: #EAF0F5 !important; }

    /* Radio-based nav — give selected item a terminal-prompt look */
    section[data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 6px 4px;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox div, .stNumberInput input {
        color: #D7DEE8 !important;
        background-color: #0A0E17 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    .stButton>button {
        background-color: #16331F;
        color: #39FF6A !important;
        border-radius: 2px;
        border: 1px solid #2E6B42;
        padding: 7px 18px;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .stButton>button:hover {
        background-color: #1E4A2B;
        border-color: #39FF6A;
    }

    .stDataFrame, .stDataFrame * { color: #D7DEE8 !important; font-family: 'JetBrains Mono', monospace !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =========================================================
# 2. THE FIXED DEMO SCENARIO (deliberately scoped to one domain)
# =========================================================

DEFAULT_SYSTEM_SPEC = """\
SERVICE: checkout_service.py (E-Commerce Checkout Workflow)

Entities:
- Payment Gateway: authorizes customer card payments, sends a webhook on success.
- Inventory Service: holds stock counts per SKU, decremented on order confirmation.
- Webhook Handler: receives payment-confirmation webhooks and triggers fulfillment.
- Fulfillment Worker: reserves inventory and ships the order once payment is confirmed.

Documented business rule:
"When a payment webhook is received, decrement inventory by 1 and mark the order
as fulfilled, provided the item is in stock."

Known operational context:
- The payment gateway occasionally re-sends the same webhook (at-least-once delivery).
- Multiple fulfillment workers can run concurrently during high-traffic periods.
- The team assumes each checkout session only ever receives one webhook.
"""

EVENT_LIBRARY = {
    "PAYMENT_SUCCESS": "Payment Gateway authorizes the charge and confirms success.",
    "INVENTORY_DEPLETED": "A concurrent worker decrements the shared inventory count for this SKU to zero.",
    "DUPLICATE_WEBHOOK": "The Payment Gateway re-sends the same success webhook (at-least-once delivery).",
    "AUTO_RETRY_FULFILLMENT": "The Webhook Handler triggers another fulfillment attempt in response to a webhook.",
}
ALLOWED_EVENT_TYPES = list(EVENT_LIBRARY.keys())
ORDER_VALUE = 149.00

# A small curated library of real, documented distributed-systems failure
# patterns. This stands in for the original PRD's vector database (ChromaDB) —
# instead of embeddings, we retrieve the most relevant pattern(s) using simple
# keyword overlap. This is a legitimate, simplified form of RAG: retrieve
# real reference material, then ground the agent's reasoning in it.
FAILURE_PATTERN_LIBRARY = [
    {
        "title": "Race Condition (Time-of-Check to Time-of-Use)",
        "text": "A resource is checked for a condition (e.g. stock > 0) and then acted "
                "upon in a separate step. If another process changes the resource between "
                "the check and the action, the action proceeds on stale information.",
    },
    {
        "title": "Retry Storm / Thundering Herd",
        "text": "When a downstream service slows down, naive retry logic across many "
                "workers can multiply load exponentially, amplifying a minor slowdown "
                "into a full outage.",
    },
    {
        "title": "Idempotency Failure on Duplicate Delivery",
        "text": "Messaging systems often guarantee 'at-least-once' delivery, meaning the "
                "same event can arrive twice. Systems that assume 'exactly-once' delivery "
                "will double-process duplicate events, corrupting state.",
    },
    {
        "title": "Silent Null / Missing Field Bypass",
        "text": "When a required field is missing, some validation logic silently treats "
                "it as 'no restriction' instead of failing closed, allowing invalid "
                "requests to pass undetected.",
    },
    {
        "title": "Distributed Cache Incoherence",
        "text": "A cache and its source-of-truth database can briefly disagree during "
                "concurrent writes, causing different parts of a system to act on "
                "different versions of the same fact.",
    },
    {
        "title": "Partial Failure / Split Brain",
        "text": "When part of a multi-step transaction succeeds and another part fails, "
                "systems without compensating transactions are left in an inconsistent "
                "state that neither completed nor cleanly rolled back.",
    },
]


def simple_retrieve(query_text: str, top_k: int = 2):
    """A minimal, dependency-free stand-in for vector RAG: scores each pattern
    by keyword overlap with the query and returns the top matches."""
    query_words = set(re.findall(r"[a-zA-Z]+", query_text.lower()))
    scored = []
    for entry in FAILURE_PATTERN_LIBRARY:
        entry_words = set(re.findall(r"[a-zA-Z]+", (entry["title"] + " " + entry["text"]).lower()))
        overlap = len(query_words & entry_words)
        scored.append((overlap, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]


# =========================================================
# 2B. DEMO MODE — canned, pre-verified responses, zero API calls
# =========================================================
# For a live presentation you cannot depend on network latency or API
# quota. Demo Mode returns realistic, pre-written agent outputs instantly,
# while the deterministic simulation engine (the actual "proof" part) still
# runs for real every time. Flip it off any time to show live AI calls.

DEMO_ANALYST = {
    "entities": ["Payment Gateway", "Inventory Service", "Webhook Handler", "Fulfillment Worker"],
    "relationships": [
        "Payment Gateway -> Webhook Handler",
        "Webhook Handler -> Fulfillment Worker",
        "Fulfillment Worker -> Inventory Service",
    ],
}

DEMO_ASSUMPTIONS = [
    {"id": "ASM-001", "text": "A customer's checkout session will only ever receive one payment-confirmation webhook.",
     "source": "webhook handler contract", "confidence": 91, "risk": "HIGH"},
    {"id": "ASM-002", "text": "Inventory decrements and fulfillment checks happen atomically, with no concurrent writers.",
     "source": "fulfillment worker logic", "confidence": 84, "risk": "HIGH"},
    {"id": "ASM-003", "text": "A duplicate webhook delivery is harmless because downstream logic is naturally idempotent.",
     "source": "operational assumption, undocumented", "confidence": 76, "risk": "MEDIUM"},
    {"id": "ASM-004", "text": "Retry attempts always happen sequentially, never in parallel with the original request.",
     "source": "worker pool configuration", "confidence": 68, "risk": "MEDIUM"},
]

DEMO_SCENARIO = {
    "title": "The Concurrent Abort Cascade",
    "violated_assumption": "A customer's checkout session will only ever receive one payment-confirmation webhook.",
    "events": ["PAYMENT_SUCCESS", "INVENTORY_DEPLETED", "DUPLICATE_WEBHOOK", "AUTO_RETRY_FULFILLMENT"],
}

DEMO_RECOVERY = [
    {"name": "Idempotency Key De-duplication", "mechanism": "Tag each webhook with a unique delivery ID and ignore repeats.",
     "matches_toggle": "dedup_webhook", "expected_effect": "Duplicate retries are dropped before they can trigger a second fulfillment attempt."},
    {"name": "Atomic Inventory Lock", "mechanism": "Wrap the inventory check-and-decrement in a single atomic transaction.",
     "matches_toggle": "inventory_lock", "expected_effect": "A second fulfillment attempt is safely blocked instead of over-committing stock."},
    {"name": "Circuit Breaker on Retries", "mechanism": "Trip a breaker after the first duplicate retry to halt further fulfillment attempts.",
     "matches_toggle": "circuit_breaker", "expected_effect": "The system fails safe and halts rather than corrupting the ledger."},
]

DEMO_FAILURE_EXPLANATION = (
    "The checkout session received a duplicate payment webhook while inventory for this SKU "
    "had already dropped to zero from a concurrent order. Because fulfillment logic assumed "
    "each webhook was unique, the retry triggered a second fulfillment attempt against "
    "already-depleted stock. The result is a ledger mismatch — the system believes the order "
    "was fulfilled twice, creating a $149.00 financial exposure that will require manual "
    "reconciliation if it reaches production."
)


def is_demo_mode() -> bool:
    return st.session_state.get("demo_mode", False)


# =========================================================
# 3. CLAUDE API LAYER (each function below is one "agent")
# =========================================================

def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or anthropic is None:
        return None
    return anthropic.Anthropic(api_key=api_key)


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 700) -> str:
    client = get_client()
    if client is None:
        return "__NO_API_KEY__"
    try:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(b.text for b in response.content if b.type == "text").strip()
    except Exception as e:
        return f"__ERROR__: {e}"


def extract_json(text: str):
    """Best-effort JSON extraction from an LLM response (strips code fences,
    locates the first balanced {...} or [...] block)."""
    if not text or text.startswith("__NO_API_KEY__") or text.startswith("__ERROR__"):
        return None
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue
    return None


# ---- Agent 1: System Analyst --------------------------------------------
def agent_system_analyst(spec_text: str):
    if is_demo_mode():
        return json.dumps(DEMO_ANALYST, indent=2), DEMO_ANALYST
    system_prompt = (
        "You are the System Analyst agent in an automated chaos-reasoning platform. "
        "You read raw system descriptions and extract a clean structural summary. "
        "Respond ONLY with valid JSON, no markdown fences, no commentary."
    )
    user_prompt = f"""
System description:
---
{spec_text}
---

Return JSON exactly in this shape:
{{"entities": ["Entity1", "Entity2", ...], "relationships": ["Entity1 -> Entity2", ...]}}
List 3-5 entities and 3-5 relationships based only on what's described above.
"""
    raw = call_claude(system_prompt, user_prompt, max_tokens=400)
    return raw, extract_json(raw)


# ---- Agent 2: Assumption Hunter ------------------------------------------
def agent_assumption_hunter(spec_text: str, retrieved):
    if is_demo_mode():
        return json.dumps(DEMO_ASSUMPTIONS, indent=2), DEMO_ASSUMPTIONS
    patterns_text = "\n".join(f"- {p['title']}: {p['text']}" for p in retrieved)
    system_prompt = (
        "You are the Assumption Hunter agent. You read system descriptions and surface "
        "unstated, implicit assumptions the engineers likely built on without realizing it. "
        "Ground your reasoning in the known failure patterns provided. "
        "Respond ONLY with valid JSON, no markdown fences, no commentary."
    )
    user_prompt = f"""
System description:
---
{spec_text}
---

Known relevant failure patterns (for grounding, not to be copied verbatim):
{patterns_text}

Return a JSON array of exactly 4 implicit assumptions, in this shape:
[
  {{"id": "ASM-001", "text": "...", "source": "which part of the spec this comes from",
    "confidence": 85, "risk": "HIGH"}},
  ...
]
"risk" must be one of HIGH, MEDIUM, LOW. "confidence" is 0-100.
"""
    raw = call_claude(system_prompt, user_prompt, max_tokens=700)
    return raw, extract_json(raw)


# ---- Agent 3: Paradox Generator ------------------------------------------
def agent_paradox_generator(spec_text: str, assumption_text: str, retrieved):
    if is_demo_mode():
        scenario = dict(DEMO_SCENARIO)
        scenario["violated_assumption"] = assumption_text or scenario["violated_assumption"]
        return json.dumps(scenario, indent=2), scenario
    patterns_text = "\n".join(f"- {p['title']}: {p['text']}" for p in retrieved)
    system_prompt = (
        "You are the Paradox Generator agent. You design a sequence of individually "
        "plausible events that, combined, violate a stated assumption and cause a "
        "realistic system failure. You must choose events ONLY from the allowed list "
        "given — these map to a deterministic simulation engine and cannot be invented. "
        "Respond ONLY with valid JSON, no markdown fences, no commentary."
    )
    user_prompt = f"""
System description:
---
{spec_text}
---

Assumption being attacked:
"{assumption_text}"

Relevant failure patterns for inspiration:
{patterns_text}

Allowed event types (use ONLY these exact strings, you may repeat one if it makes
the scenario more realistic, e.g. two duplicate webhooks): {ALLOWED_EVENT_TYPES}

Return JSON exactly in this shape:
{{"title": "a short punchy scenario name",
  "violated_assumption": "{assumption_text}",
  "events": ["PAYMENT_SUCCESS", "INVENTORY_DEPLETED", "DUPLICATE_WEBHOOK", "AUTO_RETRY_FULFILLMENT"]}}
Choose 3 to 6 events total, in a logical order.
"""
    raw = call_claude(system_prompt, user_prompt, max_tokens=500)
    return raw, extract_json(raw)


# ---- Agent 4: Failure Analyst --------------------------------------------
def agent_failure_analyst(sim_result: dict):
    if is_demo_mode():
        if sim_result["order_state"] == "CORRUPTED":
            return DEMO_FAILURE_EXPLANATION
        return (
            f"With the applied mitigation, the same event sequence now resolves to "
            f"{sim_result['order_state']} instead of CORRUPTED — financial exposure "
            f"dropped to ${sim_result['financial_exposure']:.2f}. The fix successfully "
            f"intercepted the failure before it could reach the ledger."
        )
    system_prompt = (
        "You are the Failure Analyst agent. You explain a deterministic simulation's "
        "output in clear, plain English for an engineering audience. You must NOT invent "
        "any numbers or facts beyond what is given to you — only explain and interpret them."
    )
    user_prompt = f"""
Deterministic simulation result (ground truth, computed by code — do not alter any numbers):
- Final order state: {sim_result['order_state']}
- Ledger mismatch occurred: {sim_result['ledger_mismatch']}
- Financial exposure: ${sim_result['financial_exposure']:.2f}
- Duplicate webhook retries: {sim_result['retry_count']}
- Final inventory count: {sim_result['final_inventory']}
- Event log:
{chr(10).join(sim_result['log'])}

Write a 3-5 sentence plain-English explanation of what happened and why it matters
to the business, suitable for a short incident summary.
"""
    return call_claude(system_prompt, user_prompt, max_tokens=350)


# ---- Agent 5: Recovery Agent ----------------------------------------------
def agent_recovery(sim_result: dict, scenario: dict):
    if is_demo_mode():
        return json.dumps(DEMO_RECOVERY, indent=2), DEMO_RECOVERY
    system_prompt = (
        "You are the Recovery Agent. You propose concrete mitigation strategies for a "
        "confirmed system failure. Each mitigation MUST map to exactly one of the three "
        "available engineering controls listed — do not invent new controls. "
        "Respond ONLY with valid JSON, no markdown fences, no commentary."
    )
    user_prompt = f"""
Scenario: {scenario.get('title', 'Unnamed scenario')}
Failure summary: order ended in state {sim_result['order_state']}, financial exposure
${sim_result['financial_exposure']:.2f}, {sim_result['retry_count']} duplicate retries.

Available engineering controls (choose from these exactly, by key):
- "dedup_webhook": De-duplicate incoming webhooks using an idempotency key so repeats are ignored.
- "inventory_lock": Use an atomic lock around inventory check-and-decrement to prevent over-commit.
- "circuit_breaker": Trip a circuit breaker after repeated retries to halt further fulfillment attempts.

Return a JSON array of up to 3 mitigations, in this shape:
[
  {{"name": "short name", "mechanism": "1-sentence description",
    "matches_toggle": "dedup_webhook", "expected_effect": "1-sentence expected outcome"}},
  ...
]
"""
    raw = call_claude(system_prompt, user_prompt, max_tokens=500)
    return raw, extract_json(raw)


# =========================================================
# 4. DETERMINISTIC SIMULATION ENGINE — "AI reasons, code verifies"
# =========================================================

def run_simulation(events: list, mitigations: dict) -> dict:
    """A plain, deterministic Python state machine. No AI involved. Given the
    same events and mitigations, this ALWAYS produces the same result."""
    inventory = 1
    payment_ok = False
    retry_count = 0
    ledger_mismatch = False
    financial_exposure = 0.0
    circuit_tripped = False
    order_state = "PENDING"
    log = []

    for ev in events:
        if ev == "PAYMENT_SUCCESS":
            payment_ok = True
            log.append(f"✅ Payment authorized successfully (${ORDER_VALUE:.2f})")

        elif ev == "INVENTORY_DEPLETED":
            if mitigations.get("inventory_lock"):
                inventory = max(inventory - 1, 0)
                log.append(f"🔒 Inventory decremented under atomic lock → {inventory} unit(s) left")
            else:
                inventory -= 1
                log.append(f"📦 Inventory decremented (no lock) → {inventory} unit(s) left")

        elif ev == "DUPLICATE_WEBHOOK":
            if mitigations.get("dedup_webhook"):
                log.append("🛡️ Duplicate webhook detected and ignored (idempotency key matched)")
            else:
                retry_count += 1
                log.append(f"⚠️ Duplicate webhook #{retry_count} received — gateway retry fired")

        elif ev == "AUTO_RETRY_FULFILLMENT":
            if circuit_tripped:
                log.append("🚫 Circuit breaker already open — retry attempt blocked")
                continue
            if mitigations.get("circuit_breaker") and retry_count >= 1:
                circuit_tripped = True
                order_state = "SAFE_HALT"
                log.append("🔌 Circuit breaker tripped — further fulfillment attempts halted")
                continue
            if mitigations.get("inventory_lock"):
                if inventory > 0:
                    inventory -= 1
                    log.append("✅ Fulfillment attempt succeeded under lock")
                else:
                    log.append("🔒 Fulfillment attempt blocked — lock prevented over-commit")
                    if order_state == "PENDING":
                        order_state = "PARTIALLY_RECOVERED"
            else:
                if inventory <= 0 and retry_count > 0:
                    ledger_mismatch = True
                    financial_exposure += ORDER_VALUE
                    order_state = "CORRUPTED"
                    log.append(f"💥 Fulfillment committed against depleted inventory → ledger mismatch (+${ORDER_VALUE:.2f} exposure)")
                else:
                    log.append("✅ Fulfillment attempt processed normally")

    if order_state == "PENDING":
        order_state = "CORRUPTED" if ledger_mismatch else "RESOLVED_CLEAN"

    return {
        "log": log,
        "order_state": order_state,
        "ledger_mismatch": ledger_mismatch,
        "financial_exposure": financial_exposure,
        "retry_count": retry_count,
        "final_inventory": inventory,
        "payment_ok": payment_ok,
    }


STATE_META = {
    "CORRUPTED": {"color": "#FF4D4D", "badge": "pe-tagchip-bad", "label": "💥 CORRUPTED"},
    "RESOLVED_CLEAN": {"color": "#39FF6A", "badge": "pe-tagchip-good", "label": "✅ RESOLVED CLEAN"},
    "PARTIALLY_RECOVERED": {"color": "#F5C542", "badge": "pe-tagchip-medium", "label": "🟡 PARTIALLY RECOVERED"},
    "SAFE_HALT": {"color": "#4FA8E0", "badge": "pe-tagchip-low", "label": "🔌 SAFE HALT"},
    "PENDING": {"color": "#8A97AC", "badge": "pe-tagchip-neutral", "label": "PENDING"},
}


def build_cascade_dot(sim_result: dict) -> str:
    state = sim_result["order_state"]
    meta = STATE_META.get(state, STATE_META["PENDING"])
    retry_fill = "#5D4037" if sim_result["retry_count"] > 0 else "#1A2240"
    exposure_fill = "#3A1B18" if sim_result["financial_exposure"] > 0 else "#1A2240"

    dot = f"""
    digraph G {{
        rankdir=LR;
        bgcolor="transparent";
        node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11,
              color="#3A4570", fontcolor="white", fillcolor="#1A2240"];
        edge [color="#5A6690", fontcolor="#9AA7C7", fontsize=9];

        A [label="Payment\\nAuthorized"];
        B [label="Inventory\\nDepleted"];
        C [label="Duplicate Webhook\\n(x{sim_result['retry_count']})", fillcolor="{retry_fill}"];
        D [label="Auto-Retry\\nFulfillment"];
        E [label="Order State:\\n{state}", fillcolor="{meta['color']}"];
        F [label="Financial Exposure:\\n${sim_result['financial_exposure']:.2f}", fillcolor="{exposure_fill}"];

        A -> B -> C -> D -> E;
        D -> F;
    }}
    """
    return dot


# =========================================================
# 5. SESSION STATE
# =========================================================

defaults = {
    "spec_text": DEFAULT_SYSTEM_SPEC,
    "analyst_result": None,
    "assumptions": None,
    "selected_assumption": None,
    "scenario": None,
    "baseline_sim": None,
    "mitigations": {"dedup_webhook": False, "inventory_lock": False, "circuit_breaker": False},
    "current_sim": None,
    "recovery_suggestions": None,
    "demo_mode": True,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def reset_all():
    for k, v in defaults.items():
        st.session_state[k] = v


# =========================================================
# 6. HEADER + SIDEBAR
# =========================================================

st.markdown(
    """
    <div class="pe-header">
        <span class="pe-tag">⚡ AUTONOMOUS CHAOS REASONING PLATFORM</span>
        <h1>Paradox Engine</h1>
        <p>"Find What Your System Was Never Designed For." — AI agents discover hidden
        assumptions, synthesize failure scenarios, and prove the blast radius before
        reality does.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

PAGES = ["🏠 overview", "🔍 discover", "💥 break", "⚙ simulate", "🩹 recover", "ℹ about"]

with st.sidebar:
    st.markdown("### ⚡ paradox_engine")
    st.caption("$ autonomous chaos reasoning")
    st.markdown("---")
    page = st.radio("NAVIGATE", PAGES, label_visibility="visible")
    st.markdown("---")
    st.session_state.demo_mode = st.checkbox(
        "🎬 Demo Mode (instant, no API calls)",
        value=st.session_state.get("demo_mode", True),
        help="Uses pre-verified canned agent responses so the demo never depends on "
             "network latency or API quota. The simulation engine still runs for real "
             "every time. Turn this off to show live Claude API calls.",
    )
    st.markdown("---")
    if st.session_state.demo_mode:
        st.info("🎬 Demo Mode active — agent responses are instant and pre-verified.")
    elif get_client() is None:
        st.warning("No ANTHROPIC_API_KEY detected. Turn on Demo Mode above, or set the key to use live AI.")
    else:
        st.success("Connected to Claude API ✅")
    st.markdown("---")
    st.caption(
        "**Core principle:** AI reasons. Code verifies. Every failure outcome you see "
        "is computed by a deterministic Python state machine — never guessed by the AI."
    )
    st.markdown("---")
    if st.button("🔄 reset_demo()", use_container_width=True):
        reset_all()
        st.rerun()


# =========================================================
# 7. PAGE ROUTING (sidebar-driven, not top tabs)
# =========================================================

# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
if page == "🏠 overview":
    st.markdown('<div class="pe-section-title">The System Under Test</div>', unsafe_allow_html=True)
    st.write(
        "This demo focuses on one real, well-documented failure class: a payment/inventory "
        "race condition in an e-commerce checkout flow. Here's the system as described to "
        "our agents:"
    )
    st.markdown(f'<div class="pe-mono">{st.session_state.spec_text}</div>', unsafe_allow_html=True)

    st.markdown('<div class="pe-section-title">The Loop</div>', unsafe_allow_html=True)

    loop_dot = """
    digraph G {
        rankdir=LR;
        bgcolor="transparent";
        node [shape=box, style="filled", fontname="JetBrains Mono", fontsize=11,
              color="#1A2130", fontcolor="#D7DEE8", fillcolor="#0A0E17", margin="0.25,0.15"];
        edge [color="#3A4A5C", fontcolor="#6E7A8E", fontsize=9, arrowsize=0.7];

        DISCOVER [label="🔍 DISCOVER\\nAssumption Hunter"];
        BREAK [label="💥 BREAK\\nParadox Generator", fillcolor="#1A0E0E", color="#4A2020"];
        SIMULATE [label="⚙ SIMULATE\\nDeterministic Engine", fillcolor="#0E1A14", color="#204A2E"];
        RECOVER [label="🩹 RECOVER\\nRecovery Agent"];
        RETEST [label="🔁 RE-TEST\\nCounterfactual Lab"];

        DISCOVER -> BREAK -> SIMULATE -> RECOVER -> RETEST;
        RETEST -> SIMULATE [label="  apply fix", style=dashed];
    }
    """
    st.graphviz_chart(loop_dot)
    st.caption(
        "This diagram is a read-only overview, not a navigation control — "
        "use the pages listed in the sidebar to move through each step."
    )

# ---------------------------------------------------------
# DISCOVER
# ---------------------------------------------------------
elif page == "🔍 discover":
    st.markdown('<div class="pe-section-title">Step 1 — System Analyst</div>', unsafe_allow_html=True)
    st.write("First, the System Analyst agent parses the raw spec into a structural summary.")

    if st.button("▶ Run System Analyst"):
        with st.spinner("Parsing system structure..."):
            raw, parsed = agent_system_analyst(st.session_state.spec_text)
        st.session_state.analyst_result = parsed if parsed else raw

    if st.session_state.analyst_result:
        result = st.session_state.analyst_result
        if isinstance(result, dict):
            colA, colB = st.columns(2)
            with colA:
                st.markdown("**Entities detected:**")
                for e in result.get("entities", []):
                    st.markdown(f"- {e}")
            with colB:
                st.markdown("**Relationships detected:**")
                for r in result.get("relationships", []):
                    st.markdown(f"- {r}")
        else:
            st.markdown(f'<div class="pe-mono">{result}</div>', unsafe_allow_html=True)

    st.markdown('<div class="pe-section-title">Step 2 — Assumption Hunter</div>', unsafe_allow_html=True)
    st.write(
        "Now the Assumption Hunter agent scans the spec for unstated beliefs the "
        "engineers probably didn't realize they were relying on — grounded against a "
        "small library of real distributed-systems failure patterns (retrieved by "
        "keyword relevance)."
    )

    if st.button("▶ Run Assumption Hunter"):
        retrieved = simple_retrieve(st.session_state.spec_text)
        with st.spinner("Hunting for hidden assumptions..."):
            raw, parsed = agent_assumption_hunter(st.session_state.spec_text, retrieved)
        st.session_state.assumptions = parsed
        if parsed is None:
            st.error("Could not parse AI response as JSON. Raw response below:")
            st.markdown(f'<div class="pe-mono">{raw}</div>', unsafe_allow_html=True)

    if st.session_state.assumptions:
        st.caption("Retrieved reference patterns used to ground this analysis:")
        for p in simple_retrieve(st.session_state.spec_text):
            st.caption(f"📚 *{p['title']}*")

        for a in st.session_state.assumptions:
            risk = a.get("risk", "LOW").upper()
            risk_class = {"HIGH": "pe-panel-risk-high", "MEDIUM": "pe-panel-risk-medium", "LOW": "pe-panel-risk-low"}.get(risk, "pe-panel-risk-low")
            chip_class = {"HIGH": "pe-tagchip-high", "MEDIUM": "pe-tagchip-medium", "LOW": "pe-tagchip-low"}.get(risk, "pe-tagchip-low")
            st.markdown(
                f"""
                <div class="pe-panel {risk_class}">
                    <span class="pe-tagchip {chip_class}">{risk} RISK</span>
                    &nbsp;<b>{a.get('id', '')}</b> — {a.get('confidence', '?')}% confidence
                    <p style="margin:8px 0 2px 0;">"{a.get('text', '')}"</p>
                    <p style="margin:0; font-size:12px; color:#6E7A8E;">source: {a.get('source', 'n/a')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"⚔ attack_assumption({a.get('id', '')})", key=f"attack_{a.get('id','')}"):
                st.session_state.selected_assumption = a.get("text", "")
                st.success(f"Selected. Now go to the **💥 Break** page to generate a paradox scenario for this assumption.")

# ---------------------------------------------------------
# BREAK
# ---------------------------------------------------------
elif page == "💥 break":
    st.markdown('<div class="pe-section-title">Step 3 — Paradox Generator</div>', unsafe_allow_html=True)

    if not st.session_state.selected_assumption:
        st.info("No assumption selected yet. Go to **🔍 Discover**, run the Assumption Hunter, and click 'Attack this assumption' on one.")
    else:
        st.write(f"**Attacking assumption:** \"{st.session_state.selected_assumption}\"")

        if st.button("▶ Generate Paradox Scenario"):
            retrieved = simple_retrieve(st.session_state.selected_assumption)
            with st.spinner("Synthesizing a combinatorial failure scenario..."):
                raw, parsed = agent_paradox_generator(
                    st.session_state.spec_text, st.session_state.selected_assumption, retrieved
                )
            if parsed and "events" in parsed:
                valid_events = [e for e in parsed["events"] if e in ALLOWED_EVENT_TYPES]
                parsed["events"] = valid_events if valid_events else ["PAYMENT_SUCCESS", "INVENTORY_DEPLETED", "DUPLICATE_WEBHOOK", "AUTO_RETRY_FULFILLMENT"]
                st.session_state.scenario = parsed
            else:
                st.error("Could not parse scenario JSON. Raw response below:")
                st.markdown(f'<div class="pe-mono">{raw}</div>', unsafe_allow_html=True)

    if st.session_state.scenario:
        sc = st.session_state.scenario
        st.markdown(
            f"""
            <div class="pe-panel pe-panel-risk-high">
                <h4 style="margin-top:0; color:#EAF0F5; font-family:'Space Grotesk',sans-serif;">🧨 {sc.get('title', 'Paradox Scenario')}</h4>
                <p style="color:#7C8CA0;">violates: "{sc.get('violated_assumption', '')}"</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("**Event sequence:**")
        for i, ev in enumerate(sc.get("events", []), 1):
            st.markdown(f"`{i}.` **{ev}** — {EVENT_LIBRARY.get(ev, '')}")

        st.caption("👉 Go to the **⚙ Simulate** page to run this through the deterministic engine.")

# ---------------------------------------------------------
# SIMULATE
# ---------------------------------------------------------
elif page == "⚙ simulate":
    st.markdown('<div class="pe-section-title">Step 4 — Deterministic Simulation</div>', unsafe_allow_html=True)
    st.write(
        "No AI runs here. This is a plain Python state machine — the same inputs "
        "always produce the same outputs."
    )

    if not st.session_state.scenario:
        st.info("No scenario yet. Generate one on the **💥 break** page first.")
    else:
        if st.button("▶ Run Baseline Simulation (no mitigations)"):
            events = st.session_state.scenario["events"]
            result = run_simulation(events, {"dedup_webhook": False, "inventory_lock": False, "circuit_breaker": False})
            st.session_state.baseline_sim = result
            st.session_state.current_sim = result
            st.session_state.mitigations = {"dedup_webhook": False, "inventory_lock": False, "circuit_breaker": False}

        if st.session_state.current_sim:
            sim = st.session_state.current_sim
            meta = STATE_META.get(sim["order_state"], STATE_META["PENDING"])

            badge_cls = meta["badge"]
            badge_lbl = meta["label"]
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f"**Order State**<br><span class='pe-tagchip {badge_cls}'>{badge_lbl}</span>", unsafe_allow_html=True)
            m2.metric("Financial Exposure", f"${sim['financial_exposure']:.2f}")
            m3.metric("Duplicate Retries", sim["retry_count"])
            m4.metric("Final Inventory", sim["final_inventory"])

            st.markdown("**Event log:**")
            st.markdown(f'<div class="pe-mono">{chr(10).join(sim["log"])}</div>', unsafe_allow_html=True)

            st.markdown('<div class="pe-section-title">Cascade Map</div>', unsafe_allow_html=True)
            st.graphviz_chart(build_cascade_dot(sim))

            if st.button("🧠 Explain this failure (Failure Analyst agent)"):
                with st.spinner("Analyzing failure trace..."):
                    explanation = agent_failure_analyst(sim)
                st.info(explanation)

            st.markdown('<div class="pe-section-title">📦 Reality Forge — Export Reproduction</div>', unsafe_allow_html=True)
            fixture = {
                "scenario": st.session_state.scenario,
                "mitigations_applied": st.session_state.mitigations,
                "simulation_result": sim,
                "generated_at": datetime.now().isoformat(),
            }
            st.download_button(
                "⬇️ Download reproduction fixture (JSON)",
                data=json.dumps(fixture, indent=2),
                file_name="paradox_reproduction.json",
                mime="application/json",
            )
            st.caption("👉 Go to the **🩹 recover** page to fix this and re-test.")

# ---------------------------------------------------------
# RECOVER
# ---------------------------------------------------------
elif page == "🩹 recover":
    st.markdown('<div class="pe-section-title">Step 5 — Recovery Agent</div>', unsafe_allow_html=True)

    if not st.session_state.baseline_sim:
        st.info("Run a baseline simulation on the **⚙ simulate** page first.")
    else:
        if st.button("▶ Get Recovery Suggestions"):
            with st.spinner("Drafting mitigation strategies..."):
                raw, parsed = agent_recovery(st.session_state.baseline_sim, st.session_state.scenario or {})
            st.session_state.recovery_suggestions = parsed
            if parsed is None:
                st.error("Could not parse recovery JSON. Raw response below:")
                st.markdown(f'<div class="pe-mono">{raw}</div>', unsafe_allow_html=True)

        if st.session_state.recovery_suggestions:
            for i, rec in enumerate(st.session_state.recovery_suggestions):
                st.markdown(
                    f"""
                    <div class="pe-panel">
                        <b>{rec.get('name', 'Mitigation')}</b>
                        <p style="margin:6px 0;">{rec.get('mechanism', '')}</p>
                        <p style="margin:0; font-size:12.5px; color:#6E7A8E;">expected: {rec.get('expected_effect', '')}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                toggle_key = rec.get("matches_toggle")
                if toggle_key in st.session_state.mitigations:
                    if st.button(f"✅ Apply & Re-Test — {rec.get('name','')}", key=f"apply_{i}"):
                        st.session_state.mitigations[toggle_key] = True
                        new_result = run_simulation(st.session_state.scenario["events"], st.session_state.mitigations)
                        st.session_state.current_sim = new_result
                        st.success(f"Applied. New order state: {STATE_META.get(new_result['order_state'], {}).get('label', new_result['order_state'])}")

        st.markdown('<div class="pe-section-title">🔁 Counterfactual Lab</div>', unsafe_allow_html=True)
        st.write("Manually toggle controls and instantly re-run the deterministic simulation — no AI call needed.")

        c1, c2, c3 = st.columns(3)
        with c1:
            dedup = st.checkbox("Enable webhook de-duplication", value=st.session_state.mitigations["dedup_webhook"])
        with c2:
            lock = st.checkbox("Enable atomic inventory lock", value=st.session_state.mitigations["inventory_lock"])
        with c3:
            breaker = st.checkbox("Enable circuit breaker", value=st.session_state.mitigations["circuit_breaker"])

        if st.button("🔁 Re-Run Simulation with These Settings"):
            st.session_state.mitigations = {
                "dedup_webhook": dedup, "inventory_lock": lock, "circuit_breaker": breaker,
            }
            new_result = run_simulation(st.session_state.scenario["events"], st.session_state.mitigations)
            st.session_state.current_sim = new_result

        if st.session_state.current_sim:
            sim = st.session_state.current_sim
            meta = STATE_META.get(sim["order_state"], STATE_META["PENDING"])
            badge_cls2 = meta["badge"]
            badge_lbl2 = meta["label"]
            st.markdown(f"**Current result:** <span class='pe-tagchip {badge_cls2}'>{badge_lbl2}</span>", unsafe_allow_html=True)
            st.graphviz_chart(build_cascade_dot(sim))

# ---------------------------------------------------------
# ABOUT
# ---------------------------------------------------------
elif page == "ℹ about":
    st.markdown('<div class="pe-section-title">About Paradox Engine</div>', unsafe_allow_html=True)
    st.markdown(
        """
        **Paradox Engine** is an autonomous chaos-reasoning platform. Instead of only
        testing whether a system works under expected conditions, it deploys specialized
        AI agents to actively hunt for the hidden assumptions your team never wrote down
        — and then proves, deterministically, exactly how they break.

        **The five agents:**
        1. **System Analyst** — parses a raw system description into entities and relationships
        2. **Assumption Hunter** — surfaces implicit beliefs the engineers relied on, grounded against real documented failure patterns
        3. **Paradox Generator** — designs a combinatorial sequence of individually-valid events that violates an assumption
        4. **Simulation Engine** *(not an AI — plain deterministic Python)* — computes the exact outcome
        5. **Recovery Agent** — proposes concrete engineering fixes, which you can apply and instantly re-test

        **Core principle:** *AI reasons. Code verifies.* The simulation outcome is never
        guessed by a language model — it's computed by the same kind of deterministic
        state machine a real engineering team would trust.

        **Hackathon scope note:** this build deliberately focuses on one fully-realized
        scenario (a payment/inventory race condition) rather than claiming to ingest
        arbitrary systems — exactly as a disciplined MVP should.
        """
    )