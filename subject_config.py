"""
Subject Intelligence — Complete IB Subject List, Per-Subject Config & Syllabus Topics

Provides three data structures:
  1. IB_SUBJECTS — complete catalogue of ~100 IB subjects by group
  2. SUBJECT_CONFIG — per-subject assessment, IA, boundaries, strategies, pitfalls
  3. SYLLABUS_TOPICS — topic-by-topic syllabus coverage for top subjects
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Data classes ───────────────────────────────────────────────────────

@dataclass
class AssessmentComponent:
    name: str               # "Paper 1"
    description: str        # "Multiple choice (30 questions)"
    duration_minutes: int
    weighting_pct: int
    marks: int
    hl_only: bool = False


@dataclass
class SubjectConfig:
    assessment_sl: list[AssessmentComponent]
    assessment_hl: list[AssessmentComponent]
    ia_description: str
    ia_word_limit: str
    ia_weighting_pct: int
    key_command_terms: dict[str, str]   # {term: usage note for this subject}
    grade_boundaries_hl: dict[int, int] # {grade: approx min %}
    grade_boundaries_sl: dict[int, int]
    study_strategies: list[str]
    common_pitfalls: list[str]
    category: str  # "science"|"humanities"|"language_lit"|"language_acq"|"math"|"arts"|"core"


@dataclass
class SyllabusTopic:
    id: str              # "bio_1"
    name: str            # "Cell Biology"
    subtopics: list[str] # ["Cell theory", "Ultrastructure of cells", ...]
    hl_only: bool = False


# ── 1. Complete IB Subject List ────────────────────────────────────────

# Languages use display patterns: "English A: Literature", "French B", "Spanish Ab Initio"
_LANGUAGE_A_BASES = [
    "English", "French", "Spanish", "German", "Mandarin", "Arabic", "Japanese",
    "Korean", "Portuguese", "Italian", "Dutch", "Swedish", "Norwegian", "Danish",
    "Finnish", "Russian", "Turkish",
]

_LANGUAGE_B_OPTIONS = [
    "French B", "Spanish B", "German B", "Mandarin B", "Arabic B", "Japanese B",
    "Korean B", "Portuguese B", "Italian B", "Dutch B", "Swedish B", "Norwegian B",
    "Danish B", "Finnish B", "Russian B", "Turkish B", "Hindi B", "Indonesian B",
    "Thai B",
]

_AB_INITIO_OPTIONS = [
    "French Ab Initio", "Spanish Ab Initio", "German Ab Initio",
    "Mandarin Ab Initio", "Arabic Ab Initio", "Japanese Ab Initio",
    "Italian Ab Initio",
]

IB_SUBJECTS: dict[str, list[str]] = {
    "Group 1 — Language & Literature": (
        [f"{lang} A: Language & Literature" for lang in _LANGUAGE_A_BASES]
        + [f"{lang} A: Literature" for lang in _LANGUAGE_A_BASES]
        + ["Literature and Performance"]
    ),
    "Group 2 — Language Acquisition": (
        _LANGUAGE_B_OPTIONS
        + _AB_INITIO_OPTIONS
        + ["Latin", "Classical Greek"]
    ),
    "Group 3 — Individuals & Societies": [
        "History",
        "Geography",
        "Economics",
        "Psychology",
        "Philosophy",
        "Business Management",
        "Global Politics",
        "Environmental Systems & Societies",
        "Digital Society",
        "Social and Cultural Anthropology",
        "World Religions",
    ],
    "Group 4 — Sciences": [
        "Biology",
        "Chemistry",
        "Physics",
        "Computer Science",
        "Design Technology",
        "Sports Exercise and Health Science",
        "Environmental Systems & Societies",
    ],
    "Group 5 — Mathematics": [
        "Mathematics: Analysis & Approaches",
        "Mathematics: Applications & Interpretation",
    ],
    "Group 6 — The Arts": [
        "Visual Arts",
        "Music",
        "Theatre",
        "Film",
        "Dance",
    ],
    "Core": [
        "Theory of Knowledge",
        "Extended Essay",
    ],
}


# ── 2. Subject Configuration ──────────────────────────────────────────

_DEFAULT_BOUNDARIES_HL: dict[int, int] = {7: 80, 6: 70, 5: 60, 4: 50, 3: 40, 2: 25, 1: 0}
_DEFAULT_BOUNDARIES_SL: dict[int, int] = {7: 80, 6: 70, 5: 60, 4: 50, 3: 40, 2: 25, 1: 0}


def _language_a_config(variant: str = "Literature") -> SubjectConfig:
    """Template factory for Language A subjects."""
    is_ll = "Language" in variant
    return SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Guided literary analysis" if not is_ll else "Guided textual analysis", 75, 35, 20),
            AssessmentComponent("Paper 2", "Comparative essay", 105, 35, 30),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Guided literary analysis" if not is_ll else "Guided textual analysis", 135, 35, 40),
            AssessmentComponent("Paper 2", "Comparative essay", 105, 25, 30),
            AssessmentComponent("HL Essay", "1200-1500 word essay on a literary/language topic", 0, 20, 20, hl_only=True),
        ],
        ia_description="Individual Oral: 15-minute oral exam with 10 mins prepared + 5 mins follow-up questions, connecting a literary work to a global issue.",
        ia_word_limit="N/A (oral exam)",
        ia_weighting_pct=30 if not is_ll else 20,
        key_command_terms={
            "Analyse": "Break down literary/language techniques and their effects",
            "Compare": "Identify similarities and differences between texts with specific evidence",
            "Evaluate": "Make a judgement about a text's effectiveness with supporting evidence",
            "Discuss": "Explore multiple perspectives on a literary/language question",
        },
        grade_boundaries_hl=_DEFAULT_BOUNDARIES_HL.copy(),
        grade_boundaries_sl=_DEFAULT_BOUNDARIES_SL.copy(),
        study_strategies=[
            "Annotate texts for literary/language techniques — build a personal glossary",
            "Practice timed Paper 1 analyses to improve unseen text skills",
            "Create comparison matrices for Paper 2 texts",
            "Record practice Individual Orals and self-assess",
        ],
        common_pitfalls=[
            "Retelling the plot instead of analysing technique and effect",
            "Not using subject-specific terminology (e.g. 'metaphor', 'register', 'syntax')",
            "Failing to connect analysis to authorial purpose or reader impact",
            "One-sided arguments in comparative essays — address both texts equally",
        ],
        category="language_lit",
    )


def _language_b_config() -> SubjectConfig:
    """Template factory for Language B subjects."""
    return SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Productive skills — writing", 75, 25, 30),
            AssessmentComponent("Paper 2", "Receptive skills — reading", 75, 50, 40),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Productive skills — writing", 90, 25, 30),
            AssessmentComponent("Paper 2", "Receptive skills — reading and listening", 120, 50, 65),
        ],
        ia_description="Individual Oral: Discussion based on a visual stimulus linked to a prescribed theme and a literary work (HL) or a cultural text (SL).",
        ia_word_limit="N/A (oral exam)",
        ia_weighting_pct=25,
        key_command_terms={
            "Describe": "Provide detailed characteristics of a topic in the target language",
            "Compare": "Identify similarities and differences, using appropriate connectors",
            "Explain": "Give reasons or causes using clear, structured target language",
            "Justify": "Support opinions with evidence and examples in the target language",
        },
        grade_boundaries_hl=_DEFAULT_BOUNDARIES_HL.copy(),
        grade_boundaries_sl=_DEFAULT_BOUNDARIES_SL.copy(),
        study_strategies=[
            "Read authentic target-language sources daily (news, blogs, literature)",
            "Practice all five prescribed themes with topic-specific vocabulary lists",
            "Complete timed writing tasks with proper text-type conventions (article, letter, blog)",
            "Listen to target-language podcasts and practice note-taking",
        ],
        common_pitfalls=[
            "Using English syntax patterns instead of target-language structures",
            "Limited vocabulary range — relying on basic words",
            "Not matching the text type conventions (e.g. formal letter format)",
            "Failing to link the literary work to the prescribed theme in the IO",
        ],
        category="language_acq",
    )


def _ab_initio_config() -> SubjectConfig:
    """Template factory for Ab Initio subjects."""
    return SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Productive skills — writing", 60, 25, 30),
            AssessmentComponent("Paper 2", "Receptive skills — reading", 75, 50, 40),
        ],
        assessment_hl=[],  # Ab Initio is SL only
        ia_description="Individual Oral: Conversation about a visual stimulus linked to a prescribed theme.",
        ia_word_limit="N/A (oral exam)",
        ia_weighting_pct=25,
        key_command_terms={
            "Describe": "Provide basic characteristics in simple target language",
            "State": "Give a clear, simple answer",
        },
        grade_boundaries_hl={},
        grade_boundaries_sl=_DEFAULT_BOUNDARIES_SL.copy(),
        study_strategies=[
            "Focus on the five prescribed themes and core vocabulary for each",
            "Practice basic text types: letter, email, blog post",
            "Use flashcards for vocabulary building with spaced repetition",
            "Practice speaking with a partner or recording yourself regularly",
        ],
        common_pitfalls=[
            "Attempting complex structures beyond Ab Initio level expectations",
            "Not learning text type conventions (greeting, sign-off formats)",
            "Insufficient vocabulary — aim for the prescribed word list",
        ],
        category="language_acq",
    )


SUBJECT_CONFIG: dict[str, SubjectConfig] = {
    # ── Sciences ────────────────────────────────────────────────────
    "Biology": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Multiple choice and data-based questions", 90, 36, 55),
            AssessmentComponent("Paper 2", "Short answer and extended response", 90, 44, 65),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Multiple choice and data-based questions", 120, 36, 75),
            AssessmentComponent("Paper 2", "Short answer and extended response", 150, 44, 90),
        ],
        ia_description="Scientific investigation: Design and carry out an experiment, analyse data, and evaluate methodology. Must include a focused research question, appropriate methodology, and thorough analysis.",
        ia_word_limit="6-12 pages",
        ia_weighting_pct=20,
        key_command_terms={
            "Draw": "Produce a labeled biological diagram — accuracy of structures matters",
            "Explain": "Give detailed reasons; in Biology, link structure to function",
            "Outline": "Brief summary — key points only, no full explanation needed",
            "Evaluate": "Assess strengths and limitations — common in experiment evaluation",
            "Analyse": "Break down data/processes and identify patterns or relationships",
            "Annotate": "Add brief notes to a diagram or graph to explain key features",
            "Compare": "State similarities AND differences — must have both",
            "Deduce": "Reach a conclusion from given information — show reasoning",
        },
        grade_boundaries_hl={7: 78, 6: 68, 5: 56, 4: 44, 3: 32, 2: 20, 1: 0},
        grade_boundaries_sl={7: 76, 6: 66, 5: 54, 4: 42, 3: 30, 2: 18, 1: 0},
        study_strategies=[
            "Draw and label diagrams repeatedly — examiners expect labeled diagrams",
            "Create process flowcharts for cellular respiration, photosynthesis, DNA replication",
            "Practice data-based questions from past papers — focus on graph interpretation",
            "Learn key experiments and their methodology for each topic",
            "Use mnemonics for classification and molecular structures",
        ],
        common_pitfalls=[
            "Not drawing diagrams when the question asks you to — this is a Biology requirement",
            "Confusing 'describe' (what happens) with 'explain' (why it happens)",
            "Writing 'it' without specifying the molecule, organelle, or process",
            "Forgetting to label axes, units, or include a title on graphs in the IA",
            "Not linking structure to function — a core Biology concept",
        ],
        category="science",
    ),

    "Chemistry": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Multiple choice and short answer", 90, 36, 55),
            AssessmentComponent("Paper 2", "Short answer and extended response", 90, 44, 65),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Multiple choice and short answer", 120, 36, 75),
            AssessmentComponent("Paper 2", "Short answer and extended response", 150, 44, 90),
        ],
        ia_description="Scientific investigation: Independent experimental investigation with a clear research question, appropriate methodology, and thorough data analysis. Must demonstrate personal engagement.",
        ia_word_limit="6-12 pages",
        ia_weighting_pct=20,
        key_command_terms={
            "Calculate": "Show all working with units — method marks are available for working",
            "Deduce": "Use given data to reach a conclusion — explain your reasoning",
            "Explain": "Link cause and effect using chemical principles",
            "Predict": "Use chemical theory to suggest what will happen — justify your prediction",
            "Determine": "Find the answer showing your method/calculations",
            "Compare": "Identify similarities AND differences between chemical substances/reactions",
        },
        grade_boundaries_hl={7: 80, 6: 70, 5: 58, 4: 46, 3: 34, 2: 22, 1: 0},
        grade_boundaries_sl={7: 78, 6: 68, 5: 56, 4: 44, 3: 32, 2: 20, 1: 0},
        study_strategies=[
            "Master stoichiometry calculations — they appear in almost every paper",
            "Build a data booklet familiarity sheet — know where to find key values quickly",
            "Practice balancing equations and drawing Lewis structures daily",
            "Create a periodic trends summary chart for quick reference",
            "Work through past paper calculation questions with full working shown",
        ],
        common_pitfalls=[
            "Not showing working in calculations — method marks are lost",
            "Forgetting units or giving wrong units (kJ vs kJ/mol)",
            "Not using the data booklet effectively during the exam",
            "Confusing atom economy with percentage yield",
            "Writing unbalanced equations — always check coefficients",
        ],
        category="science",
    ),

    "Physics": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Multiple choice and short answer", 90, 36, 55),
            AssessmentComponent("Paper 2", "Short answer and extended response", 90, 44, 65),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Multiple choice and short answer", 120, 36, 75),
            AssessmentComponent("Paper 2", "Short answer and extended response", 150, 44, 90),
        ],
        ia_description="Scientific investigation: Independent experimental investigation demonstrating physics principles. Must include uncertainty analysis, appropriate graphing, and evaluation of methodology.",
        ia_word_limit="6-12 pages",
        ia_weighting_pct=20,
        key_command_terms={
            "Calculate": "Show full working with correct units and significant figures",
            "Derive": "Start from known equations and show mathematical steps to reach the result",
            "Explain": "Use physics principles to describe why something occurs",
            "Sketch": "Draw an approximate graph showing the correct shape, axes labels, and key features",
            "Determine": "Find the answer from given data, showing your method",
            "State": "Give a brief, precise answer — no explanation needed",
            "Estimate": "Provide an approximate answer with order-of-magnitude reasoning",
        },
        grade_boundaries_hl={7: 76, 6: 66, 5: 54, 4: 42, 3: 30, 2: 18, 1: 0},
        grade_boundaries_sl={7: 74, 6: 64, 5: 52, 4: 40, 3: 28, 2: 16, 1: 0},
        study_strategies=[
            "Build an equation sheet organized by topic — know which equation to use when",
            "Practice unit analysis — check dimensions to verify your answer makes sense",
            "Draw free body diagrams for every mechanics problem",
            "Work through past papers under timed conditions with data booklet",
            "Understand the physics behind each equation, not just how to plug in numbers",
        ],
        common_pitfalls=[
            "Not including units in final answers — always state units",
            "Using the wrong number of significant figures (match the data given)",
            "Forgetting to convert units (km/h to m/s, degrees to radians)",
            "Not drawing diagrams for mechanics and optics problems",
            "Confusing scalar and vector quantities in calculations",
        ],
        category="science",
    ),

    # ── Humanities ──────────────────────────────────────────────────
    "Economics": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Extended response on microeconomics and macroeconomics", 75, 30, 25),
            AssessmentComponent("Paper 2", "Data response", 105, 40, 40),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Extended response on microeconomics and macroeconomics", 75, 20, 25),
            AssessmentComponent("Paper 2", "Data response", 105, 30, 40),
            AssessmentComponent("Paper 3", "HL extension — quantitative methods and policy", 105, 30, 60, hl_only=True),
        ],
        ia_description="Portfolio: Three commentaries (800 words each) based on published news articles, each covering a different section of the syllabus. Must include relevant economic diagrams.",
        ia_word_limit="800 words per commentary (3 commentaries)",
        ia_weighting_pct=20,
        key_command_terms={
            "Explain": "Use economic theory and a DIAGRAM to show cause and effect",
            "Evaluate": "Weigh advantages and disadvantages using economic evidence — reach a conclusion",
            "Discuss": "Present different economic perspectives with supporting evidence",
            "Analyse": "Break down an economic issue — use a diagram and explain the mechanism",
            "Calculate": "Show all working with correct formula — common in Paper 3",
            "Draw": "Draw a labeled economic diagram — accuracy of curves, labels, and shifts matters",
            "Distinguish": "Clearly separate two economic concepts with examples",
        },
        grade_boundaries_hl={7: 78, 6: 66, 5: 56, 4: 46, 3: 36, 2: 24, 1: 0},
        grade_boundaries_sl={7: 76, 6: 64, 5: 54, 4: 44, 3: 34, 2: 22, 1: 0},
        study_strategies=[
            "Draw diagrams for EVERY concept — examiners expect diagrams in Economics",
            "Keep a real-world examples bank organized by syllabus topic",
            "Practice Paper 2 data response under timed conditions regularly",
            "Master the key diagrams: supply/demand, AD/AS, Phillips curve, J-curve, Lorenz curve",
            "For Paper 3 HL: practice calculations with the formula sheet",
        ],
        common_pitfalls=[
            "Not including a diagram when the question says 'Explain' — this is expected in Economics",
            "Drawing diagrams without labels (axes, curves, equilibrium points, shifts)",
            "Writing one-sided evaluations — must consider both sides and reach a judgement",
            "Using generic examples instead of specific real-world cases",
            "Confusing movement along a curve with a shift of the curve",
        ],
        category="humanities",
    ),

    "History": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Source-based paper", 60, 30, 24),
            AssessmentComponent("Paper 2", "Essay paper — two essays from different topics", 90, 45, 30),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Source-based paper", 60, 20, 24),
            AssessmentComponent("Paper 2", "Essay paper — two essays from different topics", 90, 25, 30),
            AssessmentComponent("Paper 3", "HL regional option — three essays", 150, 35, 45, hl_only=True),
        ],
        ia_description="Historical investigation: Independent research on a topic of your choice (must not overlap with topics studied in class). Includes source analysis, investigation, and reflection.",
        ia_word_limit="2200 words",
        ia_weighting_pct=20,
        key_command_terms={
            "Evaluate": "Make a judgement about the value/limitations of sources or historical interpretations",
            "Discuss": "Present a balanced argument examining multiple historical perspectives",
            "Compare and contrast": "Identify similarities AND differences with specific historical evidence",
            "Analyse": "Break down causes, consequences, or significance of historical events",
            "Examine": "Consider an argument or concept in detail with supporting evidence",
            "To what extent": "Reach a judgement on degree — requires balanced argument and conclusion",
        },
        grade_boundaries_hl={7: 76, 6: 66, 5: 56, 4: 44, 3: 32, 2: 20, 1: 0},
        grade_boundaries_sl={7: 74, 6: 64, 5: 54, 4: 42, 3: 30, 2: 18, 1: 0},
        study_strategies=[
            "Create timelines for each topic — visual chronology aids recall",
            "Practice OPVL analysis (Origin, Purpose, Value, Limitation) for Paper 1",
            "Build argument structures: thesis → evidence → counter → judgement",
            "Learn 3-4 specific examples per topic for essay evidence",
            "Write timed essays regularly — practice structuring under pressure",
        ],
        common_pitfalls=[
            "Narrating events instead of analysing causes and consequences",
            "Not evaluating sources (just describing their content) in Paper 1",
            "Failing to reach a clear judgement in 'To what extent' questions",
            "Using vague generalisations instead of specific dates, names, and events",
            "Not addressing the question — writing everything you know about a topic",
        ],
        category="humanities",
    ),

    "Psychology": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Short answer and essay on the biological, cognitive, and sociocultural approaches", 120, 50, 49),
            AssessmentComponent("Paper 2", "Short answer and essay on one option", 60, 30, 22),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Short answer and essay on the biological, cognitive, and sociocultural approaches", 120, 40, 49),
            AssessmentComponent("Paper 2", "Short answer and essay on two options", 120, 20, 44),
            AssessmentComponent("Paper 3", "Research methodology questions", 60, 20, 24, hl_only=True),
        ],
        ia_description="Experimental study: Replicate or modify a published psychological study. Report includes introduction, method, results, and discussion.",
        ia_word_limit="1500-2000 words",
        ia_weighting_pct=20,
        key_command_terms={
            "Describe": "Provide a detailed account of a theory, study, or concept",
            "Evaluate": "Assess the strengths and limitations of a theory/study with evidence",
            "Discuss": "Present a balanced argument considering multiple perspectives",
            "Contrast": "Show differences between approaches, theories, or studies",
            "Explain": "Give reasons why — link cause to effect in psychological terms",
            "To what extent": "Assess the degree to which a statement is true — requires judgement",
        },
        grade_boundaries_hl={7: 76, 6: 66, 5: 54, 4: 44, 3: 34, 2: 22, 1: 0},
        grade_boundaries_sl={7: 74, 6: 64, 5: 52, 4: 42, 3: 32, 2: 20, 1: 0},
        study_strategies=[
            "Learn 2-3 studies per topic — know aim, method, results, and evaluation points",
            "Create study summary cards: researcher, year, aim, method, findings, evaluation",
            "Practice linking studies to the three approaches (biological, cognitive, sociocultural)",
            "For HL Paper 3: master research methods terminology and ethical considerations",
            "Use the GRAVE acronym for evaluation: Generalisability, Reliability, Application, Validity, Ethics",
        ],
        common_pitfalls=[
            "Describing studies without evaluating them — examiners want critical analysis",
            "Not linking studies to the relevant approach or theory",
            "Using only one study when the question asks for evidence (plural)",
            "Forgetting to discuss ethical considerations in HL Paper 3",
            "Not answering the command term — 'evaluate' requires judgement, not just description",
        ],
        category="humanities",
    ),

    "Geography": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Short answer and structured questions on core theme", 90, 35, 50),
            AssessmentComponent("Paper 2", "Extended response on optional themes", 75, 40, 40),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Short answer and structured questions on core theme", 90, 35, 50),
            AssessmentComponent("Paper 2", "Extended response on optional themes", 120, 25, 60),
            AssessmentComponent("Paper 3", "HL extension — infographic-based paper", 60, 20, 28, hl_only=True),
        ],
        ia_description="Fieldwork investigation: Collect primary data through fieldwork, analyse statistically, and evaluate. Must demonstrate understanding of geographic processes.",
        ia_word_limit="2500 words",
        ia_weighting_pct=20,
        key_command_terms={
            "Examine": "Consider a geographic argument in detail with supporting case studies",
            "Evaluate": "Assess the success or validity of geographic models/strategies with evidence",
            "Discuss": "Present different geographic perspectives with specific examples",
            "Explain": "Give reasons for geographic processes or patterns",
            "Suggest": "Propose possible reasons or solutions using geographic knowledge",
            "Compare and contrast": "Identify similarities AND differences between places/processes",
        },
        grade_boundaries_hl=_DEFAULT_BOUNDARIES_HL.copy(),
        grade_boundaries_sl=_DEFAULT_BOUNDARIES_SL.copy(),
        study_strategies=[
            "Build a case study bank: 2-3 detailed examples per topic with statistics",
            "Practice interpreting maps, graphs, and infographics (especially for HL Paper 3)",
            "Learn geographic models and theories — know their assumptions and limitations",
            "Create cause-effect-response diagrams for geographic processes",
            "Use place-specific vocabulary and named examples in every answer",
        ],
        common_pitfalls=[
            "Using generic examples instead of specific case studies with dates and data",
            "Not reading infographics carefully in HL Paper 3",
            "Failing to evaluate geographic models — just describing them is not enough",
            "Ignoring the scale of analysis (local vs national vs global)",
            "Not linking human and physical geography when questions require integration",
        ],
        category="humanities",
    ),

    "Business Management": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Case study — structured questions", 75, 35, 40),
            AssessmentComponent("Paper 2", "Structured and extended response questions", 90, 40, 50),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Case study — structured questions", 75, 25, 40),
            AssessmentComponent("Paper 2", "Structured and extended response questions", 120, 50, 70),
        ],
        ia_description="Research project: Written commentary applying business management concepts to a real organisation. Must include primary and/or secondary research.",
        ia_word_limit="1500 words (SL) / 2000 words (HL)",
        ia_weighting_pct=25,
        key_command_terms={
            "Analyse": "Break down business data or strategy and identify implications",
            "Evaluate": "Make a judgement about a business strategy/decision with evidence",
            "Discuss": "Present arguments for and against a business issue",
            "Explain": "Give reasons for a business decision or outcome",
            "Apply": "Use business concepts/tools to analyse a given situation",
            "Recommend": "Provide a justified suggestion for a course of action",
        },
        grade_boundaries_hl=_DEFAULT_BOUNDARIES_HL.copy(),
        grade_boundaries_sl=_DEFAULT_BOUNDARIES_SL.copy(),
        study_strategies=[
            "Learn business tools and frameworks (SWOT, PEST, Ansoff, Porter's) and when to apply each",
            "Practice financial ratio calculations and interpretation",
            "Build a bank of real company examples for each topic",
            "Practice case study analysis under timed conditions",
            "Create concept maps linking the four main topics together",
        ],
        common_pitfalls=[
            "Not applying concepts to the specific case study — generic answers score poorly",
            "Listing business tools without explaining WHY they apply to the situation",
            "Forgetting stakeholder perspectives in evaluation questions",
            "Not showing calculations in quantitative questions",
            "Failing to make a justified recommendation when asked to evaluate",
        ],
        category="humanities",
    ),

    "Global Politics": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Stimulus-based paper on four core units", 75, 30, 30),
            AssessmentComponent("Paper 2", "Extended response essays", 105, 45, 50),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Stimulus-based paper on four core units", 75, 20, 30),
            AssessmentComponent("Paper 2", "Extended response essays", 105, 40, 50),
            AssessmentComponent("HL Extension", "Global political challenge research", 0, 20, 20, hl_only=True),
        ],
        ia_description="Engagement activity: Written report on a political issue the student has engaged with directly. Must include personal engagement and reflection.",
        ia_word_limit="2000 words",
        ia_weighting_pct=20,
        key_command_terms={
            "Discuss": "Present balanced perspectives on a political issue with evidence",
            "Evaluate": "Assess the effectiveness or impact of political actions/institutions",
            "Examine": "Investigate in detail, considering multiple political perspectives",
            "Compare": "Identify similarities and differences between political systems or events",
            "Analyse": "Break down political situations identifying causes, effects, and stakeholders",
        },
        grade_boundaries_hl=_DEFAULT_BOUNDARIES_HL.copy(),
        grade_boundaries_sl=_DEFAULT_BOUNDARIES_SL.copy(),
        study_strategies=[
            "Keep up with current events — use quality news sources to build example banks",
            "Learn key political theories and their proponents",
            "Practice structuring balanced arguments with evidence from multiple perspectives",
            "Create comparison tables for political systems and international organizations",
        ],
        common_pitfalls=[
            "Being too opinion-based without supporting evidence",
            "Not using political science terminology",
            "Ignoring multiple perspectives (realist, liberal, constructivist)",
            "Using outdated examples when more recent ones are available",
        ],
        category="humanities",
    ),

    # ── Mathematics ─────────────────────────────────────────────────
    "Mathematics: Analysis & Approaches": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Short and extended response — no calculator", 90, 40, 80),
            AssessmentComponent("Paper 2", "Short and extended response — calculator allowed", 90, 40, 80),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Short and extended response — no calculator", 120, 30, 110),
            AssessmentComponent("Paper 2", "Short and extended response — calculator allowed", 120, 30, 110),
            AssessmentComponent("Paper 3", "Extended problems — calculator allowed", 60, 20, 55, hl_only=True),
        ],
        ia_description="Mathematical exploration: Investigate a mathematical topic of personal interest. Must demonstrate personal engagement, mathematical communication, and use of appropriate mathematics.",
        ia_word_limit="12-20 pages",
        ia_weighting_pct=20,
        key_command_terms={
            "Hence": "MUST use the previous result — do not start from scratch",
            "Show that": "Prove the given result — all steps must be shown clearly",
            "Find": "Calculate and state the answer — show working for method marks",
            "Sketch": "Draw a graph showing key features (intercepts, asymptotes, turning points)",
            "Verify": "Confirm a result using substitution or alternative method",
            "Hence or otherwise": "Using the previous result is recommended but not required",
            "Write down": "No working needed — the answer should be immediately obvious",
        },
        grade_boundaries_hl={7: 78, 6: 64, 5: 52, 4: 40, 3: 28, 2: 16, 1: 0},
        grade_boundaries_sl={7: 76, 6: 62, 5: 50, 4: 38, 3: 26, 2: 14, 1: 0},
        study_strategies=[
            "Practice Paper 1 (no calculator) separately — build mental calculation skills",
            "Learn the formula booklet inside-out — know what's given and what you must memorise",
            "Master proof techniques for HL: induction, contradiction, counterexample",
            "Practice 'Hence' and 'Show that' questions — they require specific approaches",
            "Time yourself on past papers — learn to allocate time by marks",
        ],
        common_pitfalls=[
            "'Hence' means use the previous result — starting fresh loses all marks",
            "Not showing sufficient working in 'Show that' questions",
            "Rounding too early in multi-step calculations — keep exact values until the end",
            "Forgetting to check domain restrictions (e.g. log of negative, division by zero)",
            "Not labeling graph features (intercepts, asymptotes) when asked to 'Sketch'",
        ],
        category="math",
    ),

    "Mathematics: Applications & Interpretation": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Short response — calculator allowed", 90, 40, 80),
            AssessmentComponent("Paper 2", "Extended response — calculator allowed", 90, 40, 80),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Short response — calculator allowed", 120, 30, 110),
            AssessmentComponent("Paper 2", "Extended response — calculator allowed", 120, 30, 110),
            AssessmentComponent("Paper 3", "Extended problems — calculator allowed", 60, 20, 55, hl_only=True),
        ],
        ia_description="Mathematical exploration: Apply mathematics to a real-world situation of personal interest. Strong emphasis on modelling and use of technology.",
        ia_word_limit="12-20 pages",
        ia_weighting_pct=20,
        key_command_terms={
            "Hence": "MUST use the previous result — do not start from scratch",
            "Find": "Calculate and state the answer — show working",
            "Comment": "Interpret the mathematical result in context of the real-world situation",
            "Interpret": "Explain what a mathematical result means in the given context",
            "Write down": "No working needed — the answer should be immediately obvious",
            "Estimate": "Give an approximate answer — show your reasoning",
        },
        grade_boundaries_hl={7: 76, 6: 62, 5: 50, 4: 38, 3: 26, 2: 14, 1: 0},
        grade_boundaries_sl={7: 74, 6: 60, 5: 48, 4: 36, 3: 24, 2: 12, 1: 0},
        study_strategies=[
            "Master your GDC (graphing calculator) — know how to use all statistical functions",
            "Practice interpreting results in context — 'What does this mean in real life?'",
            "Focus on modelling: linear, exponential, logistic, sinusoidal",
            "For statistics: practice hypothesis testing procedures step by step",
            "Learn to use technology effectively in the exploration (spreadsheets, Desmos, GeoGebra)",
        ],
        common_pitfalls=[
            "Not interpreting results in context — just stating a number is not enough",
            "'Hence' means use the previous result — same rule as Analysis & Approaches",
            "Not showing GDC working (state what you entered and the output)",
            "Rounding errors in multi-step statistical calculations",
            "Forgetting to state assumptions when modelling",
        ],
        category="math",
    ),

    # ── Language A (English) ────────────────────────────────────────
    "English A: Literature": _language_a_config("Literature"),
    "English A: Language & Literature": _language_a_config("Language & Literature"),

    # ── Computer Science ────────────────────────────────────────────
    "Computer Science": SubjectConfig(
        assessment_sl=[
            AssessmentComponent("Paper 1", "Short answer and structured questions on core topics", 90, 45, 70),
            AssessmentComponent("Paper 2", "Option topic — object-oriented programming", 45, 25, 45),
        ],
        assessment_hl=[
            AssessmentComponent("Paper 1", "Short answer and structured questions on core + HL extension", 130, 40, 100),
            AssessmentComponent("Paper 2", "Option topic — object-oriented programming", 45, 20, 45),
            AssessmentComponent("Paper 3", "Case study — pre-released material", 60, 20, 30, hl_only=True),
        ],
        ia_description="Solution: Develop a computational product for a real client. Must include planning, design, development, testing, and evaluation with client feedback.",
        ia_word_limit="2000 words (documentation) + product",
        ia_weighting_pct=30 if False else 20,  # SL: 30%, HL: 20%
        key_command_terms={
            "Construct": "Write pseudocode or code that solves the problem",
            "Trace": "Follow through an algorithm step by step showing variable states",
            "Outline": "Describe an algorithm or process briefly",
            "Explain": "Give reasons for a design/algorithmic choice",
            "Evaluate": "Assess the efficiency, reliability, or suitability of a solution",
            "Distinguish": "Show clear differences between two computing concepts",
        },
        grade_boundaries_hl={7: 78, 6: 68, 5: 56, 4: 44, 3: 32, 2: 20, 1: 0},
        grade_boundaries_sl={7: 76, 6: 66, 5: 54, 4: 42, 3: 30, 2: 18, 1: 0},
        study_strategies=[
            "Practice writing pseudocode and tracing algorithms by hand",
            "Learn Big-O notation and be able to analyse algorithm complexity",
            "Create summary sheets for each core topic with key definitions",
            "For HL: study the pre-released case study thoroughly before the exam",
            "Practice OOP concepts: inheritance, polymorphism, encapsulation with examples",
        ],
        common_pitfalls=[
            "Writing real code instead of IB pseudocode in Paper 1",
            "Not tracing through algorithms step by step — just stating the answer",
            "Confusing different data structures and their appropriate use cases",
            "In the IA: building without proper planning documentation",
            "Not explaining WHY a particular algorithm or data structure was chosen",
        ],
        category="science",
    ),
}

# ── Generate Language B and Ab Initio configs from templates ────────

_LANG_B_TEMPLATE = _language_b_config()
_AB_INITIO_TEMPLATE = _ab_initio_config()

for _lang_b_name in _LANGUAGE_B_OPTIONS:
    if _lang_b_name not in SUBJECT_CONFIG:
        SUBJECT_CONFIG[_lang_b_name] = _LANG_B_TEMPLATE

for _ab_name in _AB_INITIO_OPTIONS:
    if _ab_name not in SUBJECT_CONFIG:
        SUBJECT_CONFIG[_ab_name] = _AB_INITIO_TEMPLATE

# Generate Language A configs from template for non-English languages
for _lang in _LANGUAGE_A_BASES:
    for _variant in ("Literature", "Language & Literature"):
        _key = f"{_lang} A: {_variant}"
        if _key not in SUBJECT_CONFIG:
            SUBJECT_CONFIG[_key] = _language_a_config(_variant)


# ── 3. Syllabus Topics ────────────────────────────────────────────────

SYLLABUS_TOPICS: dict[str, list[SyllabusTopic]] = {
    "Biology": [
        SyllabusTopic("bio_1", "Cell Biology", [
            "Cell theory", "Ultrastructure of cells", "Membrane structure",
            "Membrane transport", "Origin of cells", "Cell division",
        ]),
        SyllabusTopic("bio_2", "Molecular Biology", [
            "Molecules to metabolism", "Water", "Carbohydrates and lipids",
            "Proteins", "Enzymes", "DNA and RNA structure",
            "DNA replication, transcription, and translation",
        ]),
        SyllabusTopic("bio_3", "Genetics", [
            "Genes", "Chromosomes", "Meiosis", "Inheritance",
            "Genetic modification and biotechnology",
        ]),
        SyllabusTopic("bio_4", "Ecology", [
            "Species, communities, and ecosystems", "Energy flow",
            "Carbon cycling", "Climate change",
        ]),
        SyllabusTopic("bio_5", "Evolution and Biodiversity", [
            "Evidence for evolution", "Natural selection",
            "Classification of biodiversity", "Cladistics",
        ]),
        SyllabusTopic("bio_6", "Human Physiology", [
            "Digestion and absorption", "The blood system",
            "Defence against infectious disease", "Gas exchange",
            "Neurons and synapses", "Hormones, homeostasis, and reproduction",
        ]),
        SyllabusTopic("bio_7", "Nucleic Acids (HL)", [
            "DNA structure and replication", "Transcription and gene expression",
            "Translation",
        ], hl_only=True),
        SyllabusTopic("bio_8", "Metabolism, Cell Respiration, and Photosynthesis (HL)", [
            "Metabolism", "Cell respiration", "Photosynthesis",
        ], hl_only=True),
        SyllabusTopic("bio_9", "Plant Biology (HL)", [
            "Transport in the xylem", "Transport in the phloem",
            "Growth in plants", "Reproduction in plants",
        ], hl_only=True),
        SyllabusTopic("bio_10", "Genetics and Evolution (HL)", [
            "Meiosis", "Inheritance", "Gene pools and speciation",
        ], hl_only=True),
        SyllabusTopic("bio_11", "Animal Physiology (HL)", [
            "Antibody production and vaccination", "Movement",
            "The kidney and osmoregulation", "Sexual reproduction",
        ], hl_only=True),
    ],

    "Chemistry": [
        SyllabusTopic("chem_1", "Stoichiometric Relationships", [
            "Introduction to the particulate nature of matter",
            "The mole concept", "Reacting masses and volumes",
        ]),
        SyllabusTopic("chem_2", "Atomic Structure", [
            "The nuclear atom", "Electron configuration",
        ]),
        SyllabusTopic("chem_3", "Periodicity", [
            "Periodic table", "Periodic trends",
        ]),
        SyllabusTopic("chem_4", "Chemical Bonding and Structure", [
            "Ionic bonding and structure", "Covalent bonding",
            "Covalent structures", "Intermolecular forces",
            "Metallic bonding",
        ]),
        SyllabusTopic("chem_5", "Energetics/Thermochemistry", [
            "Measuring energy changes", "Hess's Law",
            "Bond enthalpies",
        ]),
        SyllabusTopic("chem_6", "Chemical Kinetics", [
            "Collision theory and rates of reaction",
        ]),
        SyllabusTopic("chem_7", "Equilibrium", [
            "Equilibrium", "The equilibrium law",
        ]),
        SyllabusTopic("chem_8", "Acids and Bases", [
            "Theories of acids and bases", "Properties of acids and bases",
            "The pH scale", "Strong and weak acids and bases",
            "Acid deposition",
        ]),
        SyllabusTopic("chem_9", "Redox Processes", [
            "Oxidation and reduction", "Electrochemical cells",
        ]),
        SyllabusTopic("chem_10", "Organic Chemistry", [
            "Fundamentals of organic chemistry", "Functional group chemistry",
        ]),
        SyllabusTopic("chem_11", "Measurement and Data Processing", [
            "Uncertainties and errors in measurement",
            "Graphical techniques", "Spectroscopic identification",
        ]),
        SyllabusTopic("chem_12", "Atomic Structure (HL)", [
            "Electron configuration HL extension",
        ], hl_only=True),
        SyllabusTopic("chem_13", "The Periodic Table (HL)", [
            "First-row d-block elements", "Coloured complexes",
        ], hl_only=True),
        SyllabusTopic("chem_14", "Bonding (HL)", [
            "Covalent bonding and electron domain geometry",
            "Hybridization",
        ], hl_only=True),
        SyllabusTopic("chem_15", "Energetics (HL)", [
            "Energy cycles", "Entropy and spontaneity",
        ], hl_only=True),
        SyllabusTopic("chem_16", "Kinetics (HL)", [
            "Rate expression and reaction mechanism",
            "Activation energy",
        ], hl_only=True),
        SyllabusTopic("chem_17", "Equilibrium (HL)", [
            "The equilibrium law HL",
        ], hl_only=True),
        SyllabusTopic("chem_18", "Acids and Bases (HL)", [
            "Calculations involving acids and bases",
            "pH curves", "Buffer solutions",
        ], hl_only=True),
        SyllabusTopic("chem_19", "Redox (HL)", [
            "Electrochemical cells HL", "Standard electrode potentials",
        ], hl_only=True),
        SyllabusTopic("chem_20", "Organic Chemistry (HL)", [
            "Types of organic reactions", "Synthetic routes",
            "Stereoisomerism",
        ], hl_only=True),
    ],

    "Physics": [
        SyllabusTopic("phys_1", "Measurements and Uncertainties", [
            "Measurements in physics", "Uncertainties and errors",
            "Vectors and scalars",
        ]),
        SyllabusTopic("phys_2", "Mechanics", [
            "Motion", "Forces", "Work, energy, and power", "Momentum and impulse",
        ]),
        SyllabusTopic("phys_3", "Thermal Physics", [
            "Thermal concepts", "Modelling a gas",
        ]),
        SyllabusTopic("phys_4", "Waves", [
            "Oscillations", "Travelling waves", "Wave characteristics",
            "Wave behaviour", "Standing waves",
        ]),
        SyllabusTopic("phys_5", "Electricity and Magnetism", [
            "Electric fields", "Heating effect of electric currents",
            "Electric cells", "Magnetic effects of electric currents",
        ]),
        SyllabusTopic("phys_6", "Circular Motion and Gravitation", [
            "Circular motion", "Newton's law of gravitation",
        ]),
        SyllabusTopic("phys_7", "Atomic, Nuclear, and Particle Physics", [
            "Discrete energy and radioactivity", "Nuclear reactions",
            "The structure of matter",
        ]),
        SyllabusTopic("phys_8", "Energy Production", [
            "Energy sources", "Thermal energy transfer",
        ]),
        SyllabusTopic("phys_9", "Wave Phenomena (HL)", [
            "Simple harmonic motion", "Single-slit diffraction",
            "Interference", "Resolution", "Doppler effect",
        ], hl_only=True),
        SyllabusTopic("phys_10", "Fields (HL)", [
            "Describing fields", "Fields at work",
        ], hl_only=True),
        SyllabusTopic("phys_11", "Electromagnetic Induction (HL)", [
            "Electromagnetic induction", "Power generation and transmission",
            "Capacitance",
        ], hl_only=True),
        SyllabusTopic("phys_12", "Quantum and Nuclear Physics (HL)", [
            "The interaction of matter with radiation",
            "Nuclear physics",
        ], hl_only=True),
    ],

    "Economics": [
        SyllabusTopic("econ_1", "Introduction to Economics", [
            "What is economics?", "How do economists approach the world?",
        ]),
        SyllabusTopic("econ_2", "Microeconomics", [
            "Demand", "Supply", "Competitive market equilibrium",
            "Critique of the maximizing behaviour of consumers and producers",
            "Elasticity of demand", "Elasticity of supply",
            "Role of government in microeconomics",
            "Market failure — externalities and common pool resources",
            "Market failure — public goods", "Market failure — asymmetric information",
            "Market failure — market power",
        ]),
        SyllabusTopic("econ_3", "Macroeconomics", [
            "Measuring economic activity and illustrating its variations",
            "Variations in economic activity — aggregate demand and aggregate supply",
            "Macroeconomic objectives", "Economics of inequality and poverty",
            "Monetary policy", "Fiscal policy", "Supply-side policies",
        ]),
        SyllabusTopic("econ_4", "The Global Economy", [
            "Benefits of international trade", "Types of trade protection",
            "Arguments for and against trade control/protection",
            "Economic integration", "Exchange rates",
            "Balance of payments", "Sustainable development",
            "Measuring development", "Barriers to economic growth and development",
            "Economic growth and development strategies",
        ]),
    ],

    "History": [
        SyllabusTopic("hist_1", "Paper 1 — Prescribed Subjects", [
            "Military leaders", "Conquest and its impact",
            "The move to global war", "Rights and protest",
            "Conflict and intervention",
        ]),
        SyllabusTopic("hist_2", "Paper 2 — World History Topics", [
            "Authoritarian states (20th century)",
            "Causes and effects of 20th century wars",
            "The Cold War: superpower tensions and rivalries",
            "Rights and protest",
            "Conflict and intervention",
        ]),
        SyllabusTopic("hist_3", "Paper 3 — HL Regional Options", [
            "History of Africa and the Middle East",
            "History of the Americas",
            "History of Asia and Oceania",
            "History of Europe",
        ], hl_only=True),
    ],

    "Psychology": [
        SyllabusTopic("psych_1", "Biological Approach to Understanding Behaviour", [
            "The brain and behaviour",
            "Hormones and pheromones and their effects on behaviour",
            "Genetics and behaviour",
            "The role of animal research in understanding human behaviour",
        ]),
        SyllabusTopic("psych_2", "Cognitive Approach to Understanding Behaviour", [
            "Cognitive processing", "Reliability of cognitive processes",
            "Emotion and cognition", "Cognitive processing in the digital world",
        ]),
        SyllabusTopic("psych_3", "Sociocultural Approach to Understanding Behaviour", [
            "The individual and the group",
            "Cultural origins of behaviour and cognition",
            "The influence of globalization on individual behaviour",
        ]),
        SyllabusTopic("psych_4", "Research Methodology (HL)", [
            "Approaches to research", "Research design",
            "Ethics in research",
        ], hl_only=True),
        SyllabusTopic("psych_5", "Options", [
            "Abnormal psychology", "Developmental psychology",
            "Health psychology", "Psychology of human relationships",
        ]),
    ],

    "Mathematics: Analysis & Approaches": [
        SyllabusTopic("mathaa_1", "Number and Algebra", [
            "Sequences and series", "Arithmetic sequences",
            "Geometric sequences", "Binomial theorem",
            "Permutations and combinations (HL)",
            "Complex numbers (HL)", "Proof by induction (HL)",
            "Counting principles (HL)",
        ]),
        SyllabusTopic("mathaa_2", "Functions", [
            "Functions and their graphs", "Composite and inverse functions",
            "Transformations of functions", "Quadratic functions",
            "Rational functions", "Exponential and logarithmic functions",
            "Polynomial functions (HL)", "Odd and even functions (HL)",
        ]),
        SyllabusTopic("mathaa_3", "Geometry and Trigonometry", [
            "Geometry of 3D solids", "Trigonometric ratios and equations",
            "Trigonometric identities", "Circular functions and their graphs",
            "Vectors", "Vector applications",
        ]),
        SyllabusTopic("mathaa_4", "Statistics and Probability", [
            "Descriptive statistics", "Probability",
            "Probability distributions", "Binomial distribution",
            "Normal distribution", "Bayes' theorem (HL)",
        ]),
        SyllabusTopic("mathaa_5", "Calculus", [
            "Limits and derivatives", "Differentiation rules",
            "Applications of differentiation", "Integration",
            "Areas and volumes", "Kinematics",
            "Differential equations (HL)", "Maclaurin series (HL)",
        ]),
    ],

    "Mathematics: Applications & Interpretation": [
        SyllabusTopic("mathai_1", "Number and Algebra", [
            "Approximation and error", "Sequences and series",
            "Financial mathematics", "Modelling with functions",
        ]),
        SyllabusTopic("mathai_2", "Functions", [
            "Linear models", "Quadratic and cubic models",
            "Exponential models", "Sinusoidal models",
            "Logistic models (HL)",
        ]),
        SyllabusTopic("mathai_3", "Geometry and Trigonometry", [
            "Geometry of 3D solids", "Trigonometry",
            "Voronoi diagrams", "Graph theory (HL)",
        ]),
        SyllabusTopic("mathai_4", "Statistics and Probability", [
            "Collecting and organising data", "Statistical measures",
            "Probability", "Probability distributions",
            "Hypothesis testing", "Chi-squared test",
            "Regression analysis (HL)", "Transition matrices (HL)",
        ]),
        SyllabusTopic("mathai_5", "Calculus", [
            "Differentiation", "Integration and areas",
            "Modelling with calculus", "Differential equations (HL)",
            "Slope fields (HL)", "Coupled differential equations (HL)",
        ]),
    ],

    "English A: Literature": [
        SyllabusTopic("eng_lit_1", "Readers, Writers, and Texts", [
            "Context and meaning", "Textual analysis techniques",
            "The role of the reader", "Authorial choices and effects",
            "Literary conventions and genre",
        ]),
        SyllabusTopic("eng_lit_2", "Time and Space", [
            "Texts in cultural context", "Historical and social settings",
            "Narrative perspective and time", "Transformation of texts over time",
            "The relationship between text and context",
        ]),
        SyllabusTopic("eng_lit_3", "Intertextuality: Connecting Texts", [
            "Comparative analysis", "Thematic connections across texts",
            "Formal and stylistic connections", "Generic conventions",
            "Allusion and influence",
        ]),
        SyllabusTopic("eng_lit_4", "Literary Criticism (HL)", [
            "Approaches to literary criticism", "Feminist criticism",
            "Marxist criticism", "Postcolonial criticism", "Psychoanalytic criticism",
        ], hl_only=True),
    ],

    "English A: Language & Literature": [
        SyllabusTopic("eng_ll_1", "Readers, Writers, and Texts", [
            "Context and meaning", "Audience and purpose",
            "Textual analysis of literary and non-literary texts",
            "Authorial choices in style and structure",
        ]),
        SyllabusTopic("eng_ll_2", "Time and Space", [
            "Texts in cultural and historical context",
            "Language and identity", "Representation and ideology",
            "Mass media and popular culture",
        ]),
        SyllabusTopic("eng_ll_3", "Intertextuality: Connecting Texts", [
            "Comparative textual analysis", "Adaptation and transformation",
            "The relationship between text and image",
            "Bias, perspective, and rhetoric",
        ]),
        SyllabusTopic("eng_ll_4", "Critical Study (HL)", [
            "Approaches to language study", "Sociolinguistics",
            "Language and power", "Discourse analysis",
        ], hl_only=True),
    ],

    "Geography": [
        SyllabusTopic("geo_1", "Population Distribution — Changing Population", [
            "Population and economic development patterns",
            "Changing populations and places",
            "Demographic change and population policy",
        ]),
        SyllabusTopic("geo_2", "Global Climate — Vulnerability and Resilience", [
            "Causes of global climate change",
            "Consequences of global climate change",
            "Responses to global climate change",
        ]),
        SyllabusTopic("geo_3", "Global Resource Consumption and Security", [
            "Global trends in consumption", "Water scarcity and food insecurity",
            "Energy security", "Soil degradation",
        ]),
        SyllabusTopic("geo_4", "Power, Places, and Networks (HL)", [
            "Global interactions and global power", "Global networks and flows",
            "Human and physical influences on global interactions",
        ], hl_only=True),
        SyllabusTopic("geo_5", "Human Development and Diversity (HL)", [
            "Development opportunities and outcomes",
            "Measuring development", "Obstacles to development",
            "Gender equality and empowerment",
        ], hl_only=True),
        SyllabusTopic("geo_6", "Global Risks and Resilience (HL)", [
            "Geophysical hazards", "Mass movement hazards",
            "Disaster risk and vulnerability", "Risk management and resilience",
        ], hl_only=True),
    ],

    "Business Management": [
        SyllabusTopic("bm_1", "Introduction to Business Management", [
            "The nature of business activity", "Types of business entities",
            "Business objectives", "Stakeholders", "Growth and evolution",
            "Multinational companies (MNCs)",
        ]),
        SyllabusTopic("bm_2", "Human Resource Management", [
            "Functions and evolution of HR management",
            "Organizational structure", "Leadership and management",
            "Motivation", "Organizational and corporate cultures",
            "Industrial relations (HL)",
        ]),
        SyllabusTopic("bm_3", "Finance and Accounts", [
            "Sources of finance", "Costs and revenues",
            "Final accounts", "Profitability and liquidity ratio analysis",
            "Cash flow", "Investment appraisal (HL)",
        ]),
        SyllabusTopic("bm_4", "Marketing", [
            "The role of marketing", "Marketing planning",
            "Sales forecasting (HL)", "Market research",
            "The four Ps — Product, Price, Promotion, Place",
            "The extended marketing mix for services",
            "International marketing (HL)",
        ]),
        SyllabusTopic("bm_5", "Operations Management", [
            "The role of operations management", "Production methods",
            "Lean production and quality management",
            "Location", "Production planning (HL)",
            "Research and development (HL)", "Crisis management and contingency planning (HL)",
        ]),
    ],

    "Computer Science": [
        SyllabusTopic("cs_1", "System Fundamentals", [
            "Systems in organizations", "System design basics",
            "System backup and recovery", "Software deployment",
        ]),
        SyllabusTopic("cs_2", "Computer Organization", [
            "Computer architecture", "Secondary memory",
            "Operating systems and application systems",
            "Binary representation", "Logic gates",
        ]),
        SyllabusTopic("cs_3", "Networks", [
            "Network fundamentals", "Data transmission",
            "Wireless networking", "Network protocols",
        ]),
        SyllabusTopic("cs_4", "Computational Thinking, Problem-Solving, and Programming", [
            "Thinking procedurally", "Thinking logically",
            "Thinking ahead", "Thinking concurrently and abstractly",
            "Programming fundamentals", "Arrays and collections",
            "Sub-programs and algorithms",
        ]),
        SyllabusTopic("cs_5", "Abstract Data Structures (HL)", [
            "Stacks and queues", "Linked lists",
            "Binary trees", "Recursion",
        ], hl_only=True),
        SyllabusTopic("cs_6", "Resource Management (HL)", [
            "System resources", "Role of the operating system",
        ], hl_only=True),
        SyllabusTopic("cs_7", "Control (HL)", [
            "Centralized and distributed systems",
            "Autonomous agents and multi-agent systems",
        ], hl_only=True),
    ],

    "Environmental Systems & Societies": [
        SyllabusTopic("ess_1", "Foundations of ESS", [
            "Environmental value systems", "Systems and models",
            "Energy and equilibria", "Sustainability",
        ]),
        SyllabusTopic("ess_2", "Ecology and Conservation", [
            "Species and populations", "Communities and ecosystems",
            "Functioning of ecosystems", "Biomes, zonation, and succession",
            "Investigating ecosystems",
        ]),
        SyllabusTopic("ess_3", "Biodiversity, Conservation, and Evolution", [
            "An introduction to biodiversity", "Origins of biodiversity",
            "Threats to biodiversity", "Conservation of biodiversity",
        ]),
        SyllabusTopic("ess_4", "Water, Food, and Soil", [
            "Water resources", "Water pollution",
            "Soil systems and terrestrial food production",
            "The soil system",
        ]),
        SyllabusTopic("ess_5", "Atmospheric Systems and Societies", [
            "The atmosphere", "Stratospheric ozone",
            "Photochemical smog", "Acid deposition",
        ]),
        SyllabusTopic("ess_6", "Climate Change and Energy", [
            "Greenhouse gases and global warming",
            "Energy choices and security",
            "Climate change — causes, consequences, and mitigation",
        ]),
        SyllabusTopic("ess_7", "Human Systems and Resource Use", [
            "Human population dynamics", "Resource use in society",
            "Solid domestic waste", "Human population carrying capacity",
        ]),
    ],

    "Global Politics": [
        SyllabusTopic("gp_1", "Power, Sovereignty, and International Relations", [
            "Nature of power", "State sovereignty",
            "Legitimacy", "International organizations",
            "Balance of power and polarity",
        ]),
        SyllabusTopic("gp_2", "Human Rights", [
            "Nature and evolution of human rights",
            "Codification of human rights", "Enforcement of human rights",
            "Practice and effectiveness of human rights protection",
        ]),
        SyllabusTopic("gp_3", "Development", [
            "Contested meaning of development",
            "Factors that promote or inhibit development",
            "Pathways towards development",
            "Debates surrounding development",
        ]),
        SyllabusTopic("gp_4", "Peace and Conflict", [
            "Contested meaning of peace and conflict",
            "Causes and parties to conflict",
            "Evolution of conflict", "Conflict resolution and post-conflict transformation",
        ]),
        SyllabusTopic("gp_5", "Engagement Activity", [
            "Engagement with a political issue",
            "Research and analysis",
            "Reflection on learning",
        ]),
    ],
}


def get_subject_config(subject_name: str) -> SubjectConfig | None:
    """Look up a subject config by display name. Returns None if not configured."""
    return SUBJECT_CONFIG.get(subject_name)


def get_syllabus_topics(subject_name: str) -> list[SyllabusTopic]:
    """Return syllabus topics for a subject. Empty list if not populated."""
    return SYLLABUS_TOPICS.get(subject_name, [])


def get_all_subject_names() -> list[str]:
    """Return a flat list of all IB subject names."""
    names: list[str] = []
    for group_subjects in IB_SUBJECTS.values():
        names.extend(group_subjects)
    return sorted(set(names))
