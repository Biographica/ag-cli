## Shortlisting product spec
### Context
We are an agricultural biotechnology company specialising in gene-edited trait development. We are building a robust, auditable, configurable/flexible and crucially automatable/agentic pipeline for target identification and prioritisation. This pipeline will be *agriculture/plant science* focussed and any tools which are integrated should be as specific and valuable in a plant sciences context as possible. The goal is a maximally useful product for seed breeders, trait developers and growers. 

### High level goal (Ideal case)

We aim to provide customers with a ranked shortlist of $T$ `targets` (gene + edit suggestion) from a long-list of $L$ genes. 

Targets should be ranked according to the following criteria:

- Novelty
    
    Measure of public-domain saturation of the gene + edit mechanism combination. novelty is assessed relative to trait X in species Y, with cross-species evidence counted but downweighted.
    
    Derived from:
    
    - Literature frequency
    - Patent density
    - Known trait associations
    
    Range: 0–1
    
    Higher = more novel
    
- Efficacy / Causal Confidence
    
    A quantitative estimate of confidence that perturbing the target via the specified edit strategy will move the trait in the desired direction.
    
    May be derived from:
    
    - Model scores (e.g. long-listing model)
    - GWAS/QTL co-localisation
    - Literature precedence
    - Functional annotations
    - Orthology evidence
    - Any other bespoke analysis
    
    Range: 0–1
    
    Interpretation: Probabilistic confidence proxy (not literal probability)
    
- Pleiotropic risk
    
    Estimate of risk that perturbation will cause undesirable side effects.
    
    Derived from:
    
    - Expression breadth
    - Functional annotations
    - Essentiality
    - Literature negative precedent
    - Gene family redundancy
    
    Range: 0–1
    
    Higher = higher risk
    
- Edit-ability
    
    Feasibility of executing the specified edit **under the deployment constraints**.
    
    Derived from:
    
    - Gene structure
    - LD context
    - Editing modality compatibility
    - Local sequence constraints
    - Regulatory complexity
    
    Range: 0–1
    
    Higher = more feasible
    

**Ranking unit and presentation.** 

In the ideal case, I think that internally all scores should be computed at the `target` level (gene × editing strategy), since efficacy, risk, novelty and feasibility can be strategy-dependent. However, the primary customer-facing deliverable is a ranked **gene** list. Each gene is presented with a **recommended editing strategy** (the highest-scoring feasible target for that gene under the deployment constraints) and a small set of **alternative strategies** with their quantitative trade-offs.

In addition, we aim to provide customers with written summaries of:

- a short background of the target and associated evidence
- a written description of the proposed priority editing/perturbation strategy if applicable
- why this gene & proposed edit has the given rank and score for the specified trait
- risks with the proposed editing strategies, and alternative possible strategies, if applicable
- Mechanism of action hypotheses for that gene, if possible

<aside>
💡

**Note 1:** In the ideal case we would explicitly like to rank “gene+edit suggestion” combinations since the metrics defined above aren’t necessarily precisely defined when thinking about *just* a gene

> *Example: Pleiotropic risk*
A gene itself isn’t pleiotropic but we can associate negative pleiotropic effects associated with some gene and editing strategy. Obviously some genes are likely to have pleiotropic effects regardless of how you perturb them but this is an aggregate effect of pleiotropic effects across perturbations not necessarily just a feature of the gene.
> 

Practically, we still want to provide a gene list to customers. One could imagine having a ranking of targets (gene + edits), aggregated as follows:

```python
gene_ranking = target_ranking.groupby(gene).agg({'shortlisting score':max})
```

</aside>

<aside>
💡

**Note 2**: The project specification directly impacts **how** we might want to construct/interpret these metrics. If a customer has no ability to investigate “transgenic overexpression” editing strategies, then targets with that strategy have to score lowly on editability or we just shouldn’t be considering that strategy at all. 

</aside>

<aside>
💡

**Note 3:** The metrics above will be composite i.e. emerge from the impact of multiple different lines of evidence. Some lines of evidence will be consistent across projects while others could be project/analysis specific. We need to be able to associate different bits of evidence with different output metrics and vice versa. In our heads we have something like the figure below but we specify this in more detail in the [rough workflow](https://www.notion.so/Ideal-shortlisting-product-spec-30cff50aa0f38050b2e4e8c95a5809d8?pvs=21) section:

![Screenshot 2026-02-19 at 16.16.37.png](attachment:cdbf3d63-ec64-4dcf-ab89-f20985cf5f7e:Screenshot_2026-02-19_at_16.16.37.png)

</aside>

<aside>
💡

**Note 4**: The absolute ideal case we’re looking for (which may not be possible with Kosmos) would be a workflow which outputs scores for sub-metrics (i.e. editability, novelty, efficacy, pleiotropic risk) which would allow us to dynamically shift our shortlisting ranking by re-weighting these different features. 

The [workflow I have outlined below](https://www.notion.so/Ideal-shortlisting-product-spec-30cff50aa0f38050b2e4e8c95a5809d8?pvs=21) is one way I believe we could achieve this dynamic re-weighting. The dynamic re-weighting need not be part of the kosmos/agentic run though. 

</aside>

### Inputs

- **Controlled vocab**
    - `gene`: An input entity from long-listing
    - `editing strategy`: A defined strategy for perturbing a gene (could come from a controlled set of strategies (e.g. KO, OE) or could require more specification (e.g. flower-specific up-regulation).
    - `evidence`: Information, either per-target or cross-target, which is used to inform and influence output metric calculation
        - An `evidence item` is an atomic observation (e.g. a p-value, effect size, annotation hit, literature score, network statistic).
        - An `evidence stream` is some combination of ≥1  `evidence items` which should be treated as a unit for scoring
        - Streams should remain modular and interpretable. They should typically combine a small number of closely related evidence items and must explicitly justify their internal combination rule.
    - `normalisation_spec` A versioned, explicit mapping from the stream’s raw values across the target set to a signed score $s_{e,t}\in[-1,1]$, including outlier handling, missingness behaviour, and (optionally) background/reference set.
    - `transform_spec`: A versioned, machine-readable and executable definition of a transform. A transform must be specified as either:
        1. a JSON schema from an approved transform DSL (preferred), or
        2. a code reference + content hash + typed signature (acceptable fallback).
    - `output metric`: Customer facing metric (e.g. efficacy) which is formed from an aggregation of evidence
    - `target`: A (`gene`, `editing strategy`) combination
- **Core inputs**
    
    In each project we can assume that certain inputs will always be available:
    
    1. A project specification JSON. This will include a mixture of structured information (e.g. crop, available editing machinery etc.) and unstructured information (e.g. miscellaneous shortlisting preferences such as target diversity, novelty etc.). This must include
        - Metric weights $w_M$ for each `output metric`
        - Any project-specific defaults for reliability/applicability when missing (default: 1.0)
        - A `project_spec_id` (or content hash) used for deterministic replay
    2. A ranked long-list with associated model scores
    3. A GFF file & proteome for the organism and line of interest
    4. Standard data resources currently limited to PlantExp RNA-seq & metadata, plantTFDB if we can download and process it properly
    - 5. [IN PROGRESS] Standard pre-computed evidence for each gene, useable for downstream analysis
        - Gene expression
            - Co-expression
                
                **Once per species** we can calculate co-expression across genes and identify co-expression clusters (at the global and tissue level). From this data and these clusters we can provide, per-gene:
                
                - Cluster members
                - Cluster GO-term enrichment
                - Co-expression network centrality
                - Over/under-representation of known causal genes within the cluster of interest
                - Significant individual co-expression with known causal genes and the identity of those causal genes
            - Expression
                
                We can also calculate generic expression features per-gene such as:
                
                - Expression level in early developmental stages
                - TAU score for specificity of tissue expression
                - Expression level under generic stress conditions
                - Predicted GRN interactions with causal genes, estimated via e.g. GENIE3
                    - **Note**: This is likely best used if one can first identify studies within the RNA-seq database we provide which have project-specific relevance, otherwise it risks just identifying “general” regulators.
        - Paralogs & orthologs
            
            In addition to expression, we can pre-compute features based on sequence similarity and orthology. These features can be used to give some sense of potential functional redundancy. Some examples of these features could be:
            
            - Total number of paralogs
            - Number of highly co-expressed paralogs
            - Known functions of associated paralogs
            - Known functions of associated orthologs from related species
        - PPI
            
            Finally, we can use PPI resources such as the STRING network to identify potential hints for efficacy & pleiotropic risk including:
            
            - Local network centrality
            - Total degree of the protein of interest
            - PPI interactions with known causal genes
    - 6. Gene annotation evidence from our internal literature scoping tool
        1. **gene_direct_link (score $int \in[-5,5]$)** Is the gene directly linked to the trait? Direct linking can be defined by genetic modification of the gene affecting the trait, or by other methods such as GWAS, TWAS, directed breeding etc. Also states the evidence used to answer this question and the certainty of the evidence given the method used as well as the quality of the source. 
        2. **gene_directionality:** If the answer to 1 is yes - can directionality be concluded? Is upregulation of the target gene expected to result in an increase or decrease of the trait (here {trait_of_interest})? Which effect is expected if we knocked the gene out? 
        3. **gene_pleiotropy:** Should we suspect pleiotropy by over expressing or knocking out the target gene? To answer this question look for published articles on genetic modification of the gene of interest, its paralogs or its orthologs. 
        4. **gene_tdna_insertion_line:** Can you find T-DNA insertion lines for the target gene {gene_id}? If yes, assign a score of 1, if no, assign a score of 0. Provide evidence such as stock center IDs or URLs.
        5. **paralogs_direct_link:** Are the target gene paralogs directly linked to the trait of interest? Use the same definitions as in question 1 and provide a single score for all paralog genes combined. Strong evidence for a single paralog should result in a higher score than low-moderate evidence for many paralogs.
        6. **orthologs_direct_link:** Are the target gene orthologs directly linked to the trait of interest? Use the same definitions as in question 1 and provide a single score for all ortholog genes combined.     
    
    <aside>
    💡
    
    **Note**: In some cases a project specification could say something like “We do not want to include any genes which are known in the literature”. In this case, it’s likely that the long-list would be pre-filtered to remove any genes which have been pre-identified to be causal. However, knowing which genes have previously been identified to be causal is still useful so in such cases, it’s possible that two gene lists could be provided:
    1. the novel genes to be ranked
    2. the known causal genes for reference
    
    </aside>
    
- **Auxiliary/additional inputs**
    
    In addition, we’re currently working on a scientist-in-the-loop data curation hub which will allow us to identify & automatically process project-specific data which could be of high value in assessing a target’s relevance to a given project. 
    
    1. Bespoke project specific data we may have calculated based on curated data. For example
        1. **Mendelian randomisation/Transcriptome-wide Association Study** analysis provided per-gene estimates of effect size and significance level for linking gene expression with trait values
    2. A pre-identified list of studies (e.g. RNA-seq or bioprojects) which have been vetted by scientists and are associated with project outcomes

### Rough workflow components & outputs

There are some rough workflow steps which we think make sense given the problem and outputs we’re looking for:

- **1. Target construction**
    - Given the ***project specification*** we want to elucidate the actual editing strategies which are available to us and therefore the total list of targets (gene + edit strategy combinations) which are available to us.
    - Potentially these editing strategies should be a controlled input since we have [observed](https://www.notion.so/Ideal-shortlisting-product-spec-30cff50aa0f38050b2e4e8c95a5809d8?pvs=21) that agents can suggest editing strategies which are not allowed, even when we explicitly say e.g. “we can only do KOs”.
    
    **Output**: A total target list to be ranked.
    
- **2.** `evidence` **aggregation**
    1. Planning of additional studies and per-gene `evidence items/streams` to calculate
        
        ***Given the project specification*** and descriptions of available/approved datasets, identify key project-relevant:
        
        - **Studies** which would provide high predictive value for shortlisting. Given some [“gotchas”](https://www.notion.so/Ideal-shortlisting-product-spec-30cff50aa0f38050b2e4e8c95a5809d8?pvs=21) we have observed with prior kosmos runs, we would have a preference for identifying studies within pre-approved datasets/databases we provide.
        - Additional `edvidence items` which would be most useful to calculate to inform our evaluation of our four `output metrics` (and potentially a strategy for how these would be combined into `evidence streams`)
        
        **Output**:
        
        - A list of identified studies which have high relevance to the project and project specification, with justifications for each
        - A list of novel `evidence items/streams` to calculate, each with a definition and justification for it being relevant for influencing `output metrics`
    2. Implementation of any novel project specific `evidence items/streams`
        
        **Output**: 
        
        - A table/anndata object specifying `evidence` streams for each target
- **3. Executing a configurable, interpretable** `evidence` **integration strategy**
    
    Given the ***project specification*** and the calculated `evidence` streams (including their definitions and provenance), we need to implement a principled but pragmatic strategy for translating heterogeneous evidence into the four `output metrics`:
    
    - Novelty
    - Efficacy / Causal confidence
    - Pleiotropic risk
    - Editability
    
    We aim to balance:
    
    - Scientific motivation and interpretability
    - Cross-target comparability
    - Downstream configurability (e.g. project-specific re-weighting)
    - Robustness to missing or conflicting evidence
    
    We have a strong preference for interpretable and quantitative reasoning. Rather than attempting to compute fully specified probabilistic posteriors (which would require intractable likelihood estimates), I suggest we should adopt a pseudo-Bayesian evidence aggregation framework. 
    
    - 3.1 Metric-specific priors & specification of `evidence streams`
        
        For each `output metric`, we define a **prior score per target** (calibrated to a 0–1 scale):
        
        - **Efficacy prior:** Could be an uninformative prior or could be derived from long-list model scores - this would be defined at input
        - **Novelty prior:** Uninformative but could then be informed by literature `evidence`
        - **Pleiotropic risk prior:** Likely an uninformative prior but would obviously then be informed by `evidence` (e.g. expression breadth, network centrality)
        - **Editability prior:** Again, uninformative but updated via `evidence`
        
        In addition, we need to define, for each `output metric`, which `evidence streams` are relevant to that metric and ***how*** each `evidence stream` will be used to contribute to the `output metric`. In particular, for each `output metric` $M$ we require the agent to:
        
        - Specify a set of evidence streams $\{e_{i,M}\}_{i=1,2,...}$ that are relevant to scoring $M$.
        - For each (`evidence stream`, `output metric`) pair, the agent must specify a `role ∈ {scoring, exclusion}`.
            - If `role = scoring`, the stream contributes via a signed score $s_{e,t}\in[-1,1]$.
            - If `role = exclusion`, the stream defines an explicit exclusion rule /eq (pass/fail), evaluated consistently across the full target set.
        - Justify, and validate where possible, that the chosen evidence streams are sufficiently independent to avoid systematic “double-counting” of highly correlated inputs
        
        **Outputs**
        
        1. `output metric` priors for each target
        2. Mappings from `output metric` $M$ → relevant `evidence streams` $\{e_{i,M}\}_{i=1,2,...}$, with written justifications of the relevance of those evidence streams
            
            <aside>
            💡
            
            **Note**: Since we have multiple core `evidence items` one could imagine providing, at input time, some safe priors for mapping core `evidence streams` to `output metrics`.
            
            </aside>
            
    - 3.2 `evidence stream` scoring
        
        Each `evidence stream` defines:
        
        - **Reliability** $r_{e} \in [0,1]$
            
            Reflecting exisiting/avalable knowledge about:
            
            - Experimental directness (perturbation > association > inference)
            - Study design and replication
            - Statistical robustness
            - Species distance
            
            Reliability is treated as a property of the evidence source rather than the individual target.
            
        - **Applicability** $a_{e,M} \in [0,1]$
            
            Reflecting alignment with the project specification:
            
            - Trait relevance
            - Tissue / developmental stage
            - Environmental condition
            - Germplasm compatibility
            - Editing modality compatibility
        - **Defaults:** If `reliability` or `applicability` cannot be computed, default to 1.0 and emit a warning flag in output tables.
        - **Scope:** `reliability` is stream-level (rer_ere); `applicability` is stream×metric-level (ae,Ma_{e,M}ae,M).
    - 3.3 Batch (`evidence stream`, `target`) scoring
        
        Each `evidence stream` contributing to metric $M$ must define a **batch scoring pipeline** consisting of:
        
        1. A raw extraction function producing a vector over the full target set:
            
            $$
            \mathcal{T}\rightarrow \mathbb{R}\cup\{\text{NA}\}
            $$
            
            yielding raw values $x_{e,t}$
            
        2. A normalisation function applied to the full raw vector:
            
            $$
            \{x_{e,t}\}_{t\in\mathcal{T}} \rightarrow \{s_{e,t}\}_{t\in\mathcal{T}},\quad s_{e,t}\in[-1,1]
            $$
            
            such that:
            
            $$
            f_{e,M}:\ \mathcal{T} \rightarrow [-1,1] \\f_{e,M} = h_{e,M}\circ g_{e,M}
            $$
            
            which produces a signed score $s_{e,t}$ for every target $t \in \mathcal{T}$. 
            
        
        <aside>
        💡
        
        **Note:** This function could be a simple filter, or something more complex but *it must be explicitely specified as an output*. **We should have a bias for simple, biologically motivated and interpretable functions**.
        
        For an example of something more complex, we could imagine a function which acts differently depending on the editing strategy:
        
        ```python
        def evidence_stream_fn(gene, strategy):
            if strategy == 'KO':
        		    # i.e. this evidence stream doesn't provide any 
        		    # signal for KO targets
        		    return np.nan
        		elif strategy == 'OE':
        				...
        ```
        
        </aside>
        
        Interpretation:
        
        - $s_{e,t} > 0$: supports metric $M$
        - $s_{e,t} < 0$: contradicts metric $M$
        - $|s_{e,t}|$: strength of signal
        
        To ensure cross-target comparability, each evidence stream must specify:
        
        - **Normalisation procedure:** (e.g. percentile mapping, robust z-scoring with clipping, rank-based scaling)
            - Use **rank/percentile** scaling by default for heavy-tailed biology features.
            - Use **z-score** only for approximately symmetric distributions.
            - Always **clip** extreme values (e.g. 1st–99th percentile) before mapping to [-1,1].
            - Treat missing as 0 and track coverage separately (you already mention this).
        - **Handling of missing values:** Normalisation should occur across all target in the longlist with non-`NaN` values. Normalisation shouldn’t happen independently per target, to prevent scale drift and ensure consistent ranking.
        - For streams with `role = exclusion`, the exclusion rule $\chi_{e,M}(t)$ may be defined on raw values $x_{e,t}$ and/or on a stream-specific normalised quantity; the rule (including thresholds and missingness behaviour) must be explicit and versioned.
        - **Transform contract.** All transforms used in scoring must be specified as `transform_spec` objects (machine-readable and versioned). Free-text descriptions are permitted only as commentary and must not be required to reproduce scores. For each stream, the pipeline must output the exact `transform_spec` objects used, such that the full scoring procedure can be replayed deterministically from the input tables.
    - 3.4 Global exclusion gating (targets first, genes second)
        
        For each (`evidence stream`, `output metric`) pair with `role = exclusion`, the stream defines an explicit exclusion rule $\chi_{e,M}(t)\in\{0,1\}$ (1 = pass, 0 = exclude), evaluated consistently across the full target set.
        
        For each metric $M$, define the per-metric eligibility of a target:
        
        $$
        \chi_M(t) = \prod_{e \in \mathcal{E}_M^{\text{excl}}} \chi_{e,M}(t)
        $$
        
        We then define **global target eligibility** (excluded for any metric ⇒ globally excluded):
        
        $$
        \chi_{\text{global}}(t) = \prod_{M \in \{\text{Novelty,Efficacy,Pleiotropy,Editability}\}} \chi_M(t)
        $$
        
        Targets with $\chi_{\text{global}}(t)=0$ are excluded from all scoring and ranking outputs, and must appear in an exclusion audit report with reasons. Since the customer-facing unit is a gene, a gene is excluded only if **no globally eligible targets remain**:
        
        $$
        \chi_{\text{global}}(g) = \max_{t \in \mathcal{T}(g)} \chi_{\text{global}}(t)
        $$
        
    - 3.5 Pseudo-posterior update and target ranking logic
        
        For a given metric $M$, define the evidence streams used for scoring as $\mathcal{E}_M^{\text{score}}$ (i.e. streams with `role = scoring`).
        
        For globally eligible targets only, compute:
        
        $$
        \Delta M(t)
        =
        \chi_{\text{global}}(t)\cdot
        \sum_{e \in \mathcal{E}_M^{\text{score}}}
        s_{e,t} \cdot r_{e} \cdot a_{e,M}
        $$
        
        Final metric score:
        
        $$
        M(t)
        =
        \begin{cases}
        \sigma\big(\alpha \cdot \text{Prior}_M(t) + \beta \cdot \Delta M(t)\big), & \chi_{\text{global}}(t)=1 \\
        \text{NA}, & \chi_{\text{global}}(t)=0
        \end{cases}
        $$
        
        where:
        
        - $\sigma$ is a monotonic squashing function mapping to $[0,1]$
        - $\alpha, \beta$ are scaling parameters which should default to sensible inputs (e.g. $\alpha=\beta=1$)
        
        **Global ranking of targets**
        
        For globally eligible targets only, define an overall target score:
        
        $$
        S(t)=\sum_{M} w_M \cdot M(t),\quad \text{for } \chi_{\text{global}}(t)=1
        $$
        
        Targets are ranked by $S(t)$ descending among eligible targets. 
        
        **Global ranking of genes**
        
        Since the customer-facing unit is a gene, define the gene score and recommended strategy:
        
        $$
        S(g)=\max_{t\in\mathcal{T}(g)} S(t),\qquad
        t(g)=\arg\max_{t\in\mathcal{T}(g)} S(t)
        $$
        
        The primary deliverable is a ranked gene list by $S(g)$, where each gene is presented with:
        
        - recommended strategy $t(g)$
        - top-$N$ alternative eligible strategies $t$ with their $S(t)$ and metric breakdowns
    - 3.6 Guardrails
        
        To ensure robustness and avoid pathological rankings:
        
        1. **Comparability constraint**
            - For each evidence stream the pipeline must define:
                - Normalisation procedure
                - Handling of missing data
                - Directionality rules
                - Mapping to strength (0–1)
        2. **Conflict transparency**
            - If strong positive and strong negative evidence coexist for a target, the system should:
                - Flag evidence conflict
                - Expose contributing streams in the output summary
        3. **Coverage tracking:** For each target $t$ and metric $M$, define:
            
            $$
            \text{Coverage}(t,M)=\frac{\#\{e\in\mathcal{E}_M^{\text{score}}:\ x_{e,t}\neq \text{NA}\}}{\#\mathcal{E}_M^{\text{score}}}
            $$
            
            and define a global coverage summary (default: mean over metrics). Coverage must be reported alongside rankings and used only for audit/flags unless explicitly configured otherwise.
            
        4. Streams designated as `role = exclusion` must not be converted into scoring contributions. Exclusion is applied via $\chi_{e,M}(t)$ and produces audit output.
    - 3.7 Additional per-target hypothesis-led investigations
        - Once the target rankings have been created, we want to leave the door open for specific per-target hypothesis led analysis which could subsequently update target scoring.
        - **However**, we want to specify that if novel analysis updates target scoring, it must update via the mechanism described above in sections 3.1-5 i.e. by evaluating the new `evidence` as it links to the `output metrics`.
    
    **Output:** 
    
    1. An output table containing `evidence stream` information and how it pertains to `output metrics`
        
        ```python
        evidence_stream_id: str
        output_metric_id: str
        evidence_stream_role: Literal["exclusion", "scoring"]
        
        # raw extraction: T -> R ∪ {NA}
        raw_extraction_spec: dict  # transform_spec (DSL) OR {code_ref, code_hash, signature}
        
        # scoring only: {x_e,t} -> {s_e,t} in [-1,1]
        normalisation_spec: Optional[dict]  # transform_spec; required iff role=="scoring"
        
        # exclusion only: χ_{e,M}(t) ∈ {0,1}
        exclusion_rule_spec: Optional[dict]  # transform_spec; required iff role=="exclusion"
        
        reliability: float
        applicability: float
        justification: str  # commentary only (non-executable)
        ```
        
    2. An output table, potentially in long-format, containing the target specific attribution information 
        
        ```python
        gene: str
        edit_strategy: str
        evidence_stream_id: str
        output_metric_id: str
        evidence_stream_role: Literal["exclusion", "scoring"]
        
        raw_value: Optional[float]  # x_{e,t}
        normalised_value: Optional[float]  # intermediate (if produced)
        signed_score: Optional[float]  # s_{e,t} in [-1,1] (scoring only)
        
        excluded_by_stream: Optional[bool]  # χ_{e,M}(t) (exclusion only)
        excluded_global: bool  # χ_global(t)
        
        justification: str  # commentary only; must not be required for scoring
        ```
        
    3. Scoring functions and justifications for each evidence stream and metric, with code implementations where possible
- **4. Aggregation and creation of** `target` **dossiers for top ranking targets**
    - The intention with the outputs from section 3.1-5 is for us to have adjustable and configurable outputs which we can do downstream analysis and verification.
    - However, we also would like to create an actual top-$K$ `target` dossier for downstream outputs. Each dossier can contain highly target-specific data or insights but we would also require some core repeated information per dossier.
    - In particular, each dossier should contain:
        - Executive Summary
        - Quantitative Profile including
            - Quantitative scores for `output metrics`
            - Most influential `evidence` streams supporting each output metric
        - Mechanistic Hypothesis for the gene
        - Editing Strategy including
            - Details on the proposed editing strategy including
                - Risk & Pleiotropy Assessment
            - Potential alternative editing strategies associated with the gene. Any alternative editing strategies should also include
                - Risk & Pleiotropy Assessment
                - Comparison with the primary editing strategy, where possible
        - Key Uncertainties associated with the gene and editing strategy
        - Downstream Validation Priorities
        - Data Sources & References

## Previous tests & gotchas to be aware of using commercial scientific agents such as Kosmos
### Gotchas

We have observed some significant errors in many of the runs we have done so far:

- 1. Ignoring prompt and “fixing” with post-hoc analysis
    
    **Background**
    
    - In one example prompt, we were very explicit with Kosmos that we were only interested in ranking of novel genes.
    - To aid Kosmos, in our provided long-list parquet file, we also included a binary column indicating whether we consider that target to be novel or not based on our literature searching. We explicitly stated that genes which were marked as known should not be considered for shortlisting but were provided as references
    - Kosmos proceeded with it’s normal analysis run, generating it’s report of 4 findings based on some varied analyses it chose to execute
    
    **Errors**
    
    - Kosmos, while generating it’s PDF report, ignored the request to only focus on novel genes
    - This resulted in:
        - A completed PDF report which was provided at output
        - An initial top-15 target dossier which contained disallowed genes
    - Upon investigating the reasoning traces, Kosmos then realised post-hoc that it’s top-15 was invalid and created a new top-15 target dossier without updating the PDF report. This meant that the top-15 reported in the PDF were wrong and also inconsistent with the final top-15 which Kosmos created.
    - In addition, when it created it’s new top-15, Kosmos decided to include a completely new gene which was not part of the provided long-list
- 2. Inclusion of irrelevant datasets from the wrong organism
    
    **Background**
    
    - In one of the tests we have run, Kosmos did some interesting ChIP-seq based analysis to verify a hypothesis about a specific gene
    - This analysis was argued to be pivotal in validating a genes role in regulating a known causal gene, thereby implicating the regulator as a potential target
    
    **Error**
    
    - Upon further investigation, it seems that Kosmos selected and then used a *human* ChIP-seq dataset to support it’s analysis despite the organism of interest being arabidopsis
    - Specifically, a reasoning trace contained the following:
        
        ```markdown
        VALIDATION: Promoter analysis for CO binding sites, clock element motifs.
        Use ChIP-seq datasets (GSE50874 for CCA1/LHY) to check if COR28 is a direct target.
        ```
        
    - However, GSE50874, when we searched in NCBI, refers to a [methylation profiling dataset from the human kidney](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE50874) making the analysis obviously unuseable
- 3. Inconsistent output format
    
    Although we did specify in our prompt the specific output format we wanted for target dossiers, we found that there was inconsistent depth and style of information included when comparing across runs but also when comparing between targets in the same run. 
    

### Hard constraints

We think the gotchas point to some hard constraints we need to implement:

- Only rank targets constructed from provided longlist × allowed strategy set.
- Any external dataset must pass an organism/species match check (or be disallowed entirely).
- All outputs must be generated from a single canonical ranking table (no “PDF drift”).
- If novel-only, enforce prefilter before any reasoning and include an audit count (# excluded).
- Every claim must be backed by a citation or flagged as hypothesis.