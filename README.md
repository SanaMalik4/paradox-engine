# ⚡ Paradox Engine

### Find What Your System Was Never Designed For.

Paradox Engine is a chaos-reasoning platform built to uncover hidden assumptions in software systems, construct realistic failure scenarios, and verify their consequences through deterministic simulation.

Instead of only asking *"Does the system work?"*, Paradox Engine asks:

> **"What happens when the assumptions behind the system stop being true?"**

---

## What it does

Paradox Engine takes a realistic e-commerce checkout scenario and runs it through a five-stage reasoning and verification workflow:

**Discover → Break → Simulate → Recover → Re-Test**

### 🔍 Discover

The System Analyst identifies the major entities and relationships in the system.

The Assumption Hunter then looks for assumptions that engineers may be relying on without explicitly documenting them.

### 💥 Break

The Paradox Generator combines individually plausible events into a failure scenario designed to violate one of the discovered assumptions.

### ⚙️ Simulate

The scenario is passed to a deterministic Python simulation engine.

This is an important part of the project:

**AI reasons. Code verifies.**

The language model does not decide whether the system failed. The simulation engine calculates the outcome from the event sequence and system state.

### 🩹 Recover

The Recovery Agent proposes engineering mitigations such as:

* Webhook de-duplication
* Atomic inventory locking
* Circuit breakers

### 🔁 Re-Test

The proposed fixes can be applied to the same scenario and simulated again.

This makes it possible to compare the original failure with the counterfactual result after mitigation.

---

## The scenario

The current MVP focuses on a payment and inventory race condition in an e-commerce checkout workflow.

The simulated system contains:

* Payment Gateway
* Inventory Service
* Webhook Handler
* Fulfillment Worker

The scenario intentionally models real distributed-system problems such as:

* At-least-once webhook delivery
* Duplicate events
* Concurrent workers
* Race conditions
* Inventory depletion
* Retry behavior
* Ledger inconsistency

The goal is not to simulate every possible production system yet. The MVP focuses on making one failure scenario fully understandable and verifiable.

---

## Five-agent architecture

| Agent                 | Responsibility                                    |
| --------------------- | ------------------------------------------------- |
| **System Analyst**    | Extracts system entities and relationships        |
| **Assumption Hunter** | Finds hidden system assumptions                   |
| **Paradox Generator** | Creates realistic failure event sequences         |
| **Failure Analyst**   | Explains the verified failure and business impact |
| **Recovery Agent**    | Suggests concrete engineering mitigations         |

The simulation engine sits between the reasoning stages and acts as the verification layer.

---

## RAG-style failure pattern retrieval

The Assumption Hunter is grounded using a small curated library of documented distributed-system failure patterns.

The current library includes patterns such as:

* Race Condition / TOCTOU
* Retry Storm / Thundering Herd
* Idempotency Failure
* Silent Null / Missing Field Bypass
* Distributed Cache Incoherence
* Partial Failure / Split Brain

The MVP uses lightweight keyword retrieval rather than a vector database. This keeps the deployment simple while still grounding the agent's reasoning in known failure patterns.

---

## Deterministic simulation

The simulation engine is intentionally independent from the AI layer.

Given the same:

* Event sequence
* Inventory state
* Mitigation settings

it produces the same result every time.

The engine tracks:

* Order state
* Inventory
* Payment status
* Duplicate webhook retries
* Ledger mismatch
* Financial exposure
* Event-by-event execution log

This allows AI-generated scenarios to be tested against actual executable logic rather than relying on an LLM's description of what *might* happen.

---

## Demo Mode

Paradox Engine includes a built-in **Demo Mode**.

Demo Mode uses pre-verified agent responses instead of making live Claude API calls. The deterministic simulation still executes normally.

This makes the application suitable for:

* Hackathon demonstrations
* Offline presentations
* Reliable demos without API latency
* Demonstrations without consuming API quota

Live Claude calls can be enabled by turning Demo Mode off and providing an Anthropic API key.

---

## Tech Stack

**Frontend / Application**

* Streamlit
* Custom CSS
* Graphviz visualizations

**AI**

* Anthropic Claude API
* Five specialized agent roles

**Backend Logic**

* Python
* Deterministic state-machine simulation
* JSON-based agent outputs

**Knowledge Retrieval**

* Curated failure-pattern library
* Keyword-based retrieval

---

## Project Structure

```text
ParadoxEngine-Project/
│
├── app.py
├── requirements.txt
├── packages.txt
├── README.md
│
└── .streamlit/
    └── config.toml
```

---

## Run locally

Clone the repository and install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Then start the application:

```bash
python -m streamlit run app.py
```

The application will open in your browser.

---

## Live Claude API

Live AI mode requires an Anthropic API key.

Set the following environment variable:

```text
ANTHROPIC_API_KEY=your_api_key_here
```

Do **not** commit API keys or other secrets to GitHub.

For Streamlit Cloud deployment, the API key should be stored using Streamlit's Secrets configuration rather than hard-coded in `app.py`.

---

## Deployment

Paradox Engine is designed to run as a Streamlit application.

The intended deployment flow is:

```text
VS Code
   ↓
GitHub
   ↓
Streamlit Community Cloud
   ↓
Public Paradox Engine App
```

---

## Why Paradox Engine?

Most testing approaches check whether a system behaves correctly under expected conditions.

Paradox Engine takes a different approach.

It starts with the assumptions behind the system, deliberately challenges them, constructs a plausible chain of events, and then uses executable logic to determine whether the system survives.

**Discover the assumption.
Break the assumption.
Prove the failure.
Apply the fix.
Run it again.**

---

## Hackathon MVP

This version intentionally focuses on one deeply implemented failure scenario instead of pretending to support arbitrary system ingestion.

The architecture is designed so that future versions can expand toward:

* Custom system specifications
* Additional failure domains
* Larger pattern libraries
* More simulation models
* Custom event definitions
* Additional engineering controls
* Automated regression scenarios
* Production system integrations
