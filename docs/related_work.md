# Related work

Status: draft v0.1, updated 2026-11-09. Not exhaustive: this reflects a short
literature and web search. ClaimGuard does not claim novelty for its concept;
its aim is to build the whole chain end to end and evaluate it honestly.

## Agentic claims and fraud systems
Multi-agent claims processing is already described by vendors and in tutorials.
- Digibee, "Insurance claim analysis with AI using a multi-agent architecture":
  a claim analyst agent, a damage analyst agent and a claim reporter agent;
  high-risk claims go to investigation, others to approval.
  https://docs.digibee.com/documentation/resources/ai-practical-examples/insurance-claim-analysis-with-ai
- Oracle, "Deploying a Multi-Agent AI Fraud Detection System on OCI": an MCP
  orchestrator server coordinating data, analysis and narrative agents.
  https://docs.oracle.com/en/solutions/ai-fraud-detection/index.html
- DailyAIWorld, a LangGraph and FastMCP tutorial for an insurance claims
  workflow. It reports performance figures that I could not verify.
  https://dailyaiworld.com/workflow/build-agentic-insurance-claims-workflow-llm-fraud-detection
- StackAI, "How to Build an AI Agent for Insurance Claims Verification": an
  evidence-first, audit-ready approach with human review and risk discussion.
  https://www.stack-ai.com/insights/how-to-build-an-ai-agent-for-insurance-claims-verification
- PalTech, "AI That Acts: Designing Insurance Systems Around Multi-Agent
  Execution": a vendor whitepaper on agentic AI in insurance operations.
  https://www.pal.tech/technology/insurance-systems-with-multi-agents/

Vendor and blog material may contain unverified performance claims. ClaimGuard
reports only figures it measures itself, on synthetic data.

## Synthetic insurance fraud data
- Campo and Antonio, "An engine to simulate insurance fraud network data",
  European Actuarial Journal 15(1), 2025, pp. 255-295.
  Paper: https://arxiv.org/abs/2308.11659
  DOI: https://doi.org/10.1007/s13385-024-00399-z
  Open-source R package: https://github.com/BavoDC/iFraudSimulator
  It simulates claims linked to parties such as garages and brokers in a
  network, with controllable class imbalance, and models investigation
  outcomes as fraudulent, non-fraudulent or uninvestigated. Its authors note
  that public insurance fraud data, especially with network structure, is scarce.
- Oskarsdottir et al. (2022), on social network analytics for supervised fraud
  detection in insurance, the real-data study that the simulator above mimics
  (as cited by Campo and Antonio).

## What ClaimGuard does differently
- A Python generator with planted ground truth for vendor-linked rings in
  Canadian auto-claim style (tow, repair, clinic, rental), plus documents,
  photos and event streams, not only tabular and network data.
- A data platform around the agents: raw zone, validation, quarantine, lineage.
- A verifier that requires an evidence reference for every statement in a case
  file, with the share of unsupported statements measured.
- A comparison of the full agent against a plain model with templated reasons.
- Tests with instructions hidden in claim documents (prompt injection).

## What ClaimGuard does not claim
- It is not state of the art, and the concept is not new.
- Results on synthetic data do not show accuracy on a real insurer's claims.
- The generator is not validated against real data.
- Nothing here is legal or regulatory advice.

## Update log
- 2026-11-09: first draft.
