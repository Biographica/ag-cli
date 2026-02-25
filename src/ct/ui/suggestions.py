"""
Ghost-text suggestions for the Harvest interactive terminal.

Plant science research queries spanning the major domains Harvest supports:
genomics, expression, gene editing, orthologs, species comparison, trait
development, abiotic/biotic stress, regulatory networks, and multi-step
synthesis workflows.

Shuffled at session start so every session feels different.
"""

DEFAULT_SUGGESTIONS = [
    # ── Flowering time & photoperiod ──────────────────────────────
    "what are the key regulators of flowering time in Arabidopsis thaliana?",
    "find orthologs of FLC in Brassica napus and assess their expression",
    "which genes control vernalization response in wheat?",
    "compare photoperiod response pathways between rice and Arabidopsis",
    "what genes regulate long-day vs short-day flowering in maize?",
    "find FT orthologs in Solanum lycopersicum and assess their function",
    "what is the role of SVP in controlling floral transition?",
    "find natural variation in FLC alleles across Arabidopsis ecotypes",
    "which transcription factors regulate the autonomous flowering pathway?",
    "compare vernalization gene networks between barley and wheat",

    # ── Abiotic stress response ───────────────────────────────────
    "what genes are induced by drought stress in maize?",
    "find drought tolerance regulators in sorghum with evidence in multiple species",
    "which DREB/CBF transcription factors are induced by cold in Arabidopsis?",
    "compare salt stress response genes between rice and Arabidopsis",
    "what ABA signaling components regulate stomatal closure in barley?",
    "find heat shock factors (HSFs) in soybean and their stress-inducible expression",
    "which genes confer osmotic stress tolerance in Arabidopsis?",
    "find orthologs of AREB/ABF transcription factors in Oryza sativa",
    "what phosphorylation events activate SnRK2 kinases under drought?",
    "compare expression profiles of aquaporins under water deficit in rice vs maize",

    # ── Disease resistance & biotic stress ───────────────────────
    "find NBS-LRR disease resistance genes in Arabidopsis with known pathogen specificity",
    "what genes confer resistance to Fusarium head blight in wheat?",
    "compare R gene clusters between tomato and potato for bacterial resistance",
    "find WRKY transcription factors involved in defense signaling in rice",
    "which plant immune receptors recognize effectors from Phytophthora infestans?",
    "what is the role of NPR1 in systemic acquired resistance in Arabidopsis?",
    "find orthologs of Lr34 leaf rust resistance gene in other Triticeae species",
    "compare PTI and ETI signaling components across plant species",
    "what genes regulate jasmonate signaling in plant defense responses?",
    "find blast resistance genes (Pi) in rice with map-based cloning evidence",

    # ── Hormone signaling ─────────────────────────────────────────
    "what genes regulate auxin biosynthesis and polar transport in Arabidopsis?",
    "find cytokinin signaling components in maize and compare to Arabidopsis",
    "which gibberellin DELLA repressors are present in wheat?",
    "compare ethylene signaling pathways between tomato and Arabidopsis",
    "find strigolactone receptor orthologs in Oryza sativa",
    "what brassinosteroid signaling genes control cell elongation in rice?",
    "find salicylate pathway genes in Arabidopsis involved in SAR",
    "which JA-Ile receptors (COI1 orthologs) are found in soybean?",
    "what genes control ABA catabolism and inactivation in barley?",
    "compare hormone crosstalk networks between drought and biotic stress responses",

    # ── CRISPR and gene editing ───────────────────────────────────
    "assess CRISPR feasibility for editing FLC in Brassica napus to advance flowering",
    "find CRISPR target sites for knocking out waxy gene in maize for starch modification",
    "which genes could be edited to improve drought tolerance in rice without yield penalty?",
    "assess off-target risk for CRISPR editing of OsGW5 grain width gene in rice",
    "find candidate genes for base editing to improve nitrogen use efficiency in wheat",
    "evaluate prime editing feasibility for introducing a beneficial allele in tomato",
    "what are the CRISPR considerations for multiplexed editing in polyploid wheat?",
    "find guide RNA targets in the promoter of FT to fine-tune flowering in barley",
    "assess the gene editing landscape for improving oil composition in Brassica napus",
    "which Arabidopsis gene knockouts could be translated to crops via CRISPR?",

    # ── Transcription factors ─────────────────────────────────────
    "find MADS-box transcription factors in Arabidopsis and their developmental roles",
    "compare MYB transcription factor families between Arabidopsis and grape",
    "what NAC domain TFs regulate senescence in Arabidopsis?",
    "find bZIP transcription factors involved in ABA signaling in rice",
    "which AP2/ERF TFs respond to hypoxia in plants?",
    "compare WRKY TF family size and diversification across major crop species",
    "find B3-domain TFs that regulate seed development in Arabidopsis",
    "what SPL transcription factors are targeted by miR156 in maize?",
    "find TCP TFs involved in leaf development and their expression patterns",
    "which ARF transcription factors regulate lateral root development?",

    # ── Ortholog and comparative genomics ────────────────────────
    "find orthologs of Arabidopsis FT in 10 crop species and compare expression",
    "compare synteny between Arabidopsis and Brassica napus around the FLC locus",
    "find rice orthologs of Arabidopsis ABI5 and assess their ABA response",
    "what are the paralogs of SOC1 in Brassica and which retain flowering function?",
    "compare gene family size of WRKY TFs between monocots and dicots",
    "find Oryza sativa orthologs of Arabidopsis drought stress genes",
    "assess collinearity between wheat homoeologs for vernalization genes",
    "find soybean orthologs of Arabidopsis seed storage protein genes",
    "compare NLR immune receptor complements across Solanaceae species",
    "find poplar orthologs of Arabidopsis wood formation genes",

    # ── Expression analysis ───────────────────────────────────────
    "find tissue-specific expression patterns for flowering genes in Arabidopsis",
    "what genes are highly expressed in rice grain filling stage?",
    "compare root vs shoot expression of phosphate transporter genes in barley",
    "find genes with dawn-phased circadian expression in Arabidopsis",
    "what transcripts accumulate in the companion cells of the phloem?",
    "find stress-responsive genes with constitutive expression across tissues in maize",
    "which genes show seed coat-specific expression in Arabidopsis?",
    "compare pollen-specific gene expression between tomato and Arabidopsis",
    "find genes with opposite expression patterns in long-day vs short-day conditions",
    "what are the most highly expressed transcription factors in shoot apical meristem?",

    # ── Seed and yield traits ─────────────────────────────────────
    "find genes controlling grain size in rice and their CRISPR editing status",
    "what genes regulate seed oil composition in soybean?",
    "compare seed protein content regulators between soybean and Medicago",
    "find QTL genes for thousand grain weight in wheat",
    "what genes control endosperm development in maize?",
    "find starch biosynthesis genes in cassava with expression in storage roots",
    "which genes affect aleurone layer development in cereals?",
    "find natural variants affecting protein content in Arabidopsis seeds",
    "what genes regulate seed coat pigmentation in Arabidopsis?",
    "compare fatty acid desaturase complements in different oilseed species",

    # ── Root development ──────────────────────────────────────────
    "find genes controlling lateral root initiation in Arabidopsis",
    "what symbiosis genes enable mycorrhizal colonization in Medicago?",
    "compare root architecture genes between rice and maize",
    "find nodulation genes in soybean and their regulation by nitrogen",
    "what genes control root hair formation and elongation in Arabidopsis?",
    "find phosphate starvation response genes in rice roots",
    "which auxin pathway genes regulate primary root elongation?",
    "compare rhizobium symbiosis genes between Medicago and Lotus japonicus",
    "find genes controlling crown root development in rice",
    "what transcription factors regulate nitrogen uptake in barley roots?",

    # ── Light and circadian signaling ─────────────────────────────
    "what photoreceptors regulate shade avoidance in Arabidopsis?",
    "find circadian clock genes in rice and compare to Arabidopsis",
    "which CCA1/LHY orthologs are found in barley and what is their function?",
    "compare phytochrome gene families across monocots and dicots",
    "find cryptochrome genes in tomato and their light-regulated expression",
    "what genes link circadian clock to flowering time in Arabidopsis?",
    "find ZTL/FKF1 F-box proteins in maize and their role in photoperiod response",
    "compare evening complex genes between Arabidopsis and rice",
    "which genes integrate light and temperature signals for flowering?",
    "find TOC1/PRR orthologs in sorghum for photoperiod sensitivity engineering",

    # ── Nitrogen and nutrient use efficiency ──────────────────────
    "find high-affinity nitrate transporters in Arabidopsis and their expression",
    "compare nitrogen use efficiency genes between rice varieties",
    "what genes regulate ammonium assimilation in plants?",
    "find phosphate transporter genes upregulated by phosphate starvation in maize",
    "which genes control sulfate assimilation and transport in Arabidopsis?",
    "find genes associated with improved nitrogen use efficiency in wheat",
    "what transcription factors regulate PHO1 and PHO2 in phosphate signaling?",
    "compare iron uptake strategies between dicots and monocots",
    "find genes controlling boron transport and tolerance in plants",
    "what genes regulate potassium homeostasis under saline conditions?",

    # ── Polyploidy and genome structure ───────────────────────────
    "how do the three wheat subgenomes (A, B, D) differ for vernalization genes?",
    "find homeologous gene sets in Brassica napus and assess their divergence",
    "compare gene dosage effects in allopolyploid cotton species",
    "what genes show subgenome-biased expression in Brassica napus?",
    "find structural variants between wheat cultivars affecting yield traits",
    "compare gene family expansions in polyploid vs diploid relatives",
    "what are the consequences of subgenome dominance for trait improvement?",
    "find gene pairs where dosage balance is critical for normal development",
    "compare synteny patterns between maize subgenomes",
    "what genes show differential epigenetic regulation between wheat subgenomes?",

    # ── Multi-step research workflows ─────────────────────────────
    "comprehensive flowering time assessment in rice: genes, expression, CRISPR targets",
    "full drought tolerance gene inventory in maize with cross-species validation",
    "assess FLC as a CRISPR target in Brassica napus: orthologs, expression, guide RNAs",
    "build a gene regulatory network for cold stress response in barley",
    "compare disease resistance gene complements across Solanaceae and propose targets",
    "identify candidate genes for nitrogen use efficiency improvement in wheat",
    "find and assess MADS-box TF orthologs in soybean for yield trait modification",
    "comprehensive analysis of ABA signaling components across crop species",
    "design a CRISPR strategy to fine-tune photoperiod response in sorghum",
    "build an evidence dossier for GW5 as a rice grain quality improvement target",

    # ── Epigenetics in plants ─────────────────────────────────────
    "what chromatin remodelers regulate FLC expression in Arabidopsis?",
    "find Polycomb group genes in maize and compare to Arabidopsis",
    "which histone demethylases regulate flowering time in Arabidopsis?",
    "compare DNA methylation patterns at transposable elements in different crops",
    "find genes regulated by histone acetylation during heat stress",
    "what role does H3K27me3 play in vernalization memory in Arabidopsis?",
    "find RNA-directed DNA methylation (RdDM) pathway genes in rice",
    "which small RNA pathways regulate developmental transitions in plants?",
    "compare CHH methylation patterns between different maize tissues",
    "find genes affected by epiallelic variation in Arabidopsis natural populations",

    # ── Phenotyping and QTL ───────────────────────────────────────
    "find QTL for heading date in rice with known causal genes",
    "what GWAS loci are associated with plant height in maize?",
    "find marker-trait associations for drought tolerance in barley",
    "compare QTL collinearity for yield traits between wheat and barley",
    "what genes underlie QTL for fruit ripening in tomato?",
    "find SNPs associated with flowering time variation in soybean",
    "compare map-based cloning success stories for rice quality traits",
    "find QTL for resistance to Sclerotinia sclerotiorum in Brassica napus",
    "what genetic variants affect alpha-linolenic acid content in flaxseed?",
    "find MAS markers for rust resistance in wheat breeding programs",

    # ── Metabolic pathways ────────────────────────────────────────
    "find genes in the phenylpropanoid pathway in Arabidopsis and their expression",
    "compare glucosinolate biosynthesis genes between Arabidopsis and Brassica",
    "what genes control anthocyanin biosynthesis in grape berries?",
    "find carotenoid pathway genes in tomato with fruit-specific expression",
    "what enzymes regulate tocopherol biosynthesis in Arabidopsis seeds?",
    "compare terpenoid biosynthesis gene families between mint and Arabidopsis",
    "find genes controlling wax biosynthesis on the leaf surface in barley",
    "what genes regulate lignin composition in poplar wood?",
    "find alkaloid biosynthesis genes in tobacco with expression data",
    "compare fatty acid elongation genes between oil palm and Arabidopsis",

    # ── Post-translational regulation ─────────────────────────────
    "find E3 ubiquitin ligases regulating ABA signaling in Arabidopsis",
    "what protein kinases phosphorylate FT or its partners?",
    "find SUMO E3 ligases involved in plant stress responses",
    "which deubiquitinases regulate jasmonate signaling components?",
    "find 26S proteasome subunits that are stress-regulated in plants",
    "what RING-domain E3 ligases control auxin signaling?",
    "find autophagy pathway genes in Arabidopsis and their drought regulation",
    "which protein phosphatases (PP2C) regulate SnRK2 kinase activity?",
    "find COP1/SPA E3 ligase complex components in rice",
    "what ubiquitin-pathway components regulate DELLA protein stability?",

    # ── Literature and evidence mining ───────────────────────────
    "search PubMed for CRISPR applications to improve crop drought tolerance",
    "find recent reviews on plant temperature sensing mechanisms",
    "what does the literature say about vernalization in polyploid wheat?",
    "search for publications on GWAS for yield components in rice",
    "find recent papers on RNA interference for crop improvement",
    "search PubMed for base editing approaches to plant trait improvement",
    "what recent studies link epigenetics to transgenerational stress memory in plants?",
    "find literature on engineering C4 photosynthesis into C3 crops",
    "search for recent publications on plant pan-genomes and trait diversity",
    "find reviews on the evolution of self-incompatibility systems in plants",
]
