"""
Unified system prompt builder for the Claude Agent SDK runner.

Merges the domain knowledge primer, workflow guides, bioinformatics code-gen
hints, synthesis rules, tool catalog, and dynamic data context into a single
system prompt that Claude uses throughout the agentic loop.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("ct.system_prompt")


# ---------------------------------------------------------------------------
# Agent identity (single configurable value — change name here only)
# ---------------------------------------------------------------------------

AGENT_NAME = "Harvest"


# ---------------------------------------------------------------------------
# Identity / role preamble
# ---------------------------------------------------------------------------

_IDENTITY = f"""\
You are **{AGENT_NAME}**, an autonomous plant science research agent.

You have access to computational tools covering genomics, expression analysis,
network biology, ortholog mapping, literature search, DNA design, and data
analysis — plus a persistent Python sandbox (``run_python``) for custom analyses.

Your domain: plant biology and agricultural biotechnology. You reason about gene
function, regulatory networks, trait development, gene editing strategies,
ortholog relationships, and multi-species evidence synthesis across crop and
model plant species.

Your job: take a research question and answer it completely, using the right
tools and code, self-correcting as you go, and producing a rigorous synthesis
at the end.

## Operating Mode
- You are in an agentic loop: call tools, see results, call more tools, then
  write your final answer as plain text (no tool call).
- Think step-by-step. Use tools to gather evidence, then synthesize.
- If a tool fails or returns unhelpful data, try a different approach or use
  your own knowledge to fill gaps.
- For data analysis questions, use ``run_python`` to load data, explore it,
  and compute the answer. Variables persist between calls.
- When a species is not specified in the question, infer from context. If
  ambiguous, ask.
"""


# ---------------------------------------------------------------------------
# Synthesis instructions (injected at the end)
# ---------------------------------------------------------------------------

_SYNTHESIS_INSTRUCTIONS = """\

## When You Are Ready to Answer

Write your final answer as a direct text response (do NOT call any more tools).
Your answer should be:

1. **Complete**: Address every part of the question. Decompose the question into
   sub-parts and make sure each is answered with specifics.
2. **Accurate**: Use tool results as primary evidence. Supplement with your
   plant science knowledge. Never fabricate data.
3. **Data-rich**: Include specific gene names, expression values, ortholog
   evidence, regulatory pathway members, editing efficiency estimates, and
   species contexts.
4. **Mechanistic**: Explain the biological *why*, not just the *what* — gene
   function, pathway logic, regulatory hierarchy, evolutionary conservation.
5. **Actionable**: End with 3-5 specific experimental or analytical next steps
   (named assays, validation approaches, species to test, genomic resources).

BANNED PHRASES — never write these:
- "cannot be answered with the data retrieved"
- "failed to retrieve" / "failed to identify"
- "insufficient data" / "insufficient evidence"
- "No results were obtained"
If tools failed, pivot to answering from your plant biology knowledge instead.
"""


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_system_prompt(
    session,
    tool_names: list[str] | None = None,
    data_context: str | None = None,
    history: str | None = None,
    output_dir: str | None = None,
) -> str:
    """Build the unified system prompt for the Agent SDK runner.

    Args:
        session: Active ct Session.
        tool_names: Names of tools available in the MCP server (for reference).
        data_context: Free-text description of available data files / directories.
        history: Prior conversation turns (for interactive multi-turn sessions).
        output_dir: Path to the session output directory for saving files.

    Returns:
        The complete system prompt string.
    """
    parts: list[str] = []

    # 1. Identity
    parts.append(_IDENTITY)

    # 2. Tool catalog (concise reference — full descriptions are in MCP tool defs)
    # NOTE: The Agent SDK exposes tool names+descriptions+schemas via MCP natively.
    # We only include a brief orientation here, NOT the full tool_descriptions_for_llm()
    # which would blow up the system prompt to 155K chars and hit ARG_MAX limits.
    if tool_names:
        parts.append(f"\n## Available Tools ({len(tool_names)} total)\n")
        parts.append(
            "You have access to all tools via MCP. Key tools:\n"
            "- **run_python**: Execute Python code in a sandbox (pd, np, plt, scipy, sklearn, pysam, gseapy, pydeseq2, BioPython). Variables persist between calls.\n"
            "- **run_r**: Execute R code directly. Prefer run_r for: natural splines, wilcox.test(), p.adjust(), fisher.test(), lm()/predict(), KEGG ORA via KEGGREST, and analyses where R is the reference implementation.\n"
            "- **literature.pubmed_search**, **literature.openalex_search**, **literature.patent_search**: Literature and database search\n"
            "- **data_api.uniprot_lookup**, **data_api.ensembl_lookup**, **data_api.ncbi_gene**, **data_api.mygene_lookup**: Gene/protein data APIs\n"
            "- **genomics.gwas_lookup**, **genomics.eqtl_lookup**, **genomics.variant_annotate**: Genomics and variant tools\n"
            "- **omics.geo_search**, **omics.geo_fetch**, **omics.deseq2**, **omics.dataset_info**: Omics data discovery and analysis\n"
            "- **expression.pathway_enrichment**, **expression.diff_expression**, **expression.tf_activity**: Expression and pathway tools\n"
            "- **network.ppi_analysis**, **network.pathway_crosstalk**: Protein interaction and pathway network analysis\n"
            "- **protein.embed**, **protein.function_predict**, **protein.domain_annotate**: Protein structure and function\n"
            "- **dna.primer_design**, **dna.codon_optimize**, **dna.gibson_design**, **dna.golden_gate_design**: DNA biology and cloning\n"
            "- **singlecell.cluster**, **singlecell.trajectory**, **singlecell.cell_type_annotate**: Single-cell analysis\n"
            "\nFor data analysis questions, prefer **run_python** — it is the most powerful tool.\n"
            "For plant biology questions, combine domain tools with your expertise across species.\n"
        )

    # 2b. Output directory
    if output_dir:
        parts.append(
            f"\n## Output Directory\n"
            f"Your session output directory is: `{output_dir}`\n\n"
            f"Save ALL files here — reports, plots, CSVs, and any other artifacts.\n"
            f"- In `run_python`, use `OUTPUT_DIR` (pre-set to this path) for saving plots and data files.\n"
            f"- Use `files.write_report` and `files.write_csv` for structured output.\n"
            f"- Do NOT write to `/tmp` or other locations — all writes are restricted to this directory.\n"
        )

    # 3. Workflow guides (compact — key sequences for common tasks)
    # NOTE: The upstream workflows module contains pharma-domain workflows.
    # Plant-specific workflows will be added in a later phase. Skip for now
    # to avoid injecting pharma content into the plant science agent prompt.
    # try:
    #     from ct.agent.workflows import format_workflows_for_llm
    #     workflows = format_workflows_for_llm()
    #     if workflows:
    #         parts.append(workflows)
    # except Exception as e:
    #     logger.warning("Could not load workflows: %s", e)

    # 4. Domain knowledge primer (CRITICAL for plant science accuracy)
    # NOTE: The KNOWLEDGE_PRIMER contains plant biology domain facts and tool orientation.
    # Include in full — it grounds the agent's reasoning in plant science.
    try:
        from ct.agent.knowledge import KNOWLEDGE_PRIMER
        parts.append("\n" + KNOWLEDGE_PRIMER)
    except Exception as e:
        logger.warning("Could not load knowledge primer: %s", e)

    # 6. Bioinformatics code-gen hints (CRITICAL for BixBench performance)
    try:
        from ct.tools.code import BIOINFORMATICS_CODE_GEN_PROMPT, AGENTIC_CODE_ADDENDUM
        # Strip the template placeholders and include the raw hints
        hints = BIOINFORMATICS_CODE_GEN_PROMPT
        # Remove the {namespace_description} and {data_files_description} placeholders
        hints = hints.replace("{namespace_description}", "(see run_python tool description)")
        hints = hints.replace("{data_files_description}", "(see data context below)")
        parts.append("\n## Bioinformatics Code Generation Guide\n")
        parts.append(
            "When using ``run_python`` for bioinformatics analysis, follow these "
            "patterns and guidelines:\n"
        )
        parts.append(hints)
        parts.append(AGENTIC_CODE_ADDENDUM)
    except Exception as e:
        logger.warning("Could not load code-gen hints: %s", e)

    # 7. Synthesis rules
    try:
        from ct.agent.knowledge import SYNTHESIZER_PRIMER
        parts.append("\n## Synthesis Guidelines\n")
        parts.append(SYNTHESIZER_PRIMER)
    except Exception as e:
        logger.warning("Could not load synthesizer primer: %s", e)

    # 8. Synthesis instructions
    parts.append(_SYNTHESIS_INSTRUCTIONS)

    # 9. Dynamic data context
    if data_context:
        parts.append("\n## Data Context\n")
        parts.append(data_context)

    # 10. Session history (for multi-turn interactive mode)
    if history:
        parts.append("\n## Prior Conversation\n")
        parts.append(history)

    prompt = "\n".join(parts)
    logger.info(
        "Built system prompt: %d chars, %d sections",
        len(prompt),
        len(parts),
    )
    return prompt
