# Knowledge Layer V1

The Knowledge Layer transforms archival historical evidence into reusable, auditable historical experience without collapsing source text into unsupported opinions.

## Core flow

Source Corpus -> Evidence Links -> Historical Experience Units (HEUs) -> Insights -> Problem Relevance -> Role Selection -> Persona Response

## Hard rules

1. Every HEU must trace back to one or more canonical Source Corpus paragraph IDs.
2. HEUs record historical experience, not free-standing opinions.
3. Insights are derived from HEUs and must preserve their evidence chain.
4. Questions never bind directly to a historical person.
5. Persons are experience owners, witnesses, participants, or affected parties; they are not containers for Knowledge.
6. Role selection happens only after problem-to-knowledge matching.
7. A selected responder is treated as possessing the full experience of their complete lifetime.
8. Persona responses must first recount genuinely relevant personal experience, then provide reflection, transferable insight, and advice.
9. Taxonomy is descriptive and revisable; it must not become a rigid ontology that forces evidence into preselected categories.
10. Source Corpus remains immutable archival evidence; derived Knowledge must never overwrite or contaminate it.

## Core objects

- EvidenceLink: pointers into Source Corpus canonical IDs.
- HEU: structured historical experience unit.
- Insight: transferable interpretation derived from one or more HEUs.
- ProblemProfile: structured representation of a modern life question.
- ProblemRelevance: auditable link between a problem and HEUs/insights.
- RoleLink: records how a historical person relates to an HEU.
- ExperienceGraph: links multiple HEUs into a longitudinal life-experience chain.

## V1 objective

Build one end-to-end sample for the first product question:

> 面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？

The system must retrieve relevant experience from the Han, Tang, and Song corpus, compare candidate historical figures, and select the most appropriate responder without preassigning Tang Taizong or any other person.