# PrenatalAI — AI-Powered Prenatal Disease Detection

> Using artificial intelligence to detect prenatal diseases earlier, non-invasively, and more accurately — reducing unnecessary invasive procedures and empowering doctors worldwide through a community-driven learning platform.

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Our Solution](#our-solution)
3. [Core Architecture](#core-architecture)
4. [Key Features](#key-features)
5. [French Prenatal Ultrasound Context](#french-prenatal-ultrasound-context)
6. [Medical Context: Disease Detection Methods](#medical-context-disease-detection-methods)
7. [Technology Philosophy](#technology-philosophy)
8. [Vision & Goals](#vision--goals)

---

## The Problem

Prenatal disease detection is critical for early intervention and family planning. However, current methods face significant challenges:

### Over-reliance on Invasive Procedures

- **Amniocentesis**: A needle is inserted into the abdomen to extract amniotic fluid. Carries a ~0.5-1% miscarriage risk. Usually performed between weeks 15–20.
- **Chorionic Villus Sampling (CVS)**: Samples placental tissue (transcervically or transabdominally). Also carries miscarriage risk.
- **Cordocentesis**: Rare procedure sampling fetal blood directly from the umbilical cord.

These procedures, while accurate, cause unnecessary pain and risk when used on cases that could be ruled out non-invasively first.

### Limitations of Current AI Approaches

- Most AI systems are black boxes — doctors cannot understand why a diagnosis was made.
- Monolithic models try to detect many diseases at once, reducing accuracy.
- Equipment fragmentation: Different ultrasound machines produce different formats, making standardization difficult.
- Lack of community feedback loops: Diagnosed cases (especially false negatives) rarely improve future models.

### The Human Impact

- **3 in 1000 births** are affected by congenital heart disease.
- **1 in 700 births** is affected by Down syndrome (Trisomy 21).
- Many diseases require immediate postpartum intervention — early detection saves lives.
- Unnecessary invasive procedures cause physical pain, emotional stress, and carry measurable fetal risk.

---

## Our Solution

PrenatalAI is a **non-invasive first** diagnostic platform that uses AI analysis of standard ultrasound images to:

1. **Screen for diseases before considering invasive procedures**
2. **Prioritize the most probable diseases** for immediate attention
3. **Continuously improve** through community-driven data sharing
4. **Contextualize risk** with patient-specific parameters

The goal is **NOT to replace doctors** — it is to **empower them with better information** so they can make informed decisions and reduce unnecessary suffering.

---

## Core Architecture

### MedGemma + RAG: No-Training AI Architecture

Instead of training custom models (too slow for hackaton), we leverage **MedGemma** (Google's medical vision-language model) combined with a **Retrieval-Augmented Generation (RAG)** system. This approach requires **no model training** while enabling continuous improvement through community data.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INPUT LAYER                                │
│   Ultrasound Image(s) + Patient Context (age, history, etc.)         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SYMPTOM EXTRACTION (MedGemma)                     │
│   Prompt: "Describe all observable symptoms in this ultrasound"    │
│   Output: Structured textual symptom description                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
           ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
           │  Disease A  │  │  Disease B  │  │  Disease N  │
           │  Vector DB  │  │  Vector DB  │  │  Vector DB  │
           │  ─────────  │  │  ─────────  │  │  ─────────  │
           │  • Images   │  │  • Images   │  │  • Images   │
           │  • Text Sx  │  │  • Text Sx  │  │  • Text Sx  │
           │  • Metadata │  │  • Metadata │  │  • Metadata │
           └─────────────┘  └─────────────┘  └─────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │      PARALLEL VECTOR SEARCH     │
                    │   Query ALL disease databases   │
                    │   Retrieve top-K similar       │
                    │   symptom patterns per disease  │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      AGGREGATION LAYER          │
                    │   • Trimester-specific weights │
                    │   • Patient context priors     │
                    │   • Symptom overlap handling   │
                    │   • Ponderated mean scoring    │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │       DIAGNOSIS OUTPUT         │
                    │   ┌──────────┐ ┌──────────┐   │
                    │   │  FAST    │ │COMPREH.  │   │
                    │   │  TRACK   │ │  SCAN    │   │
                    │   │ (immediate)│(background)│   │
                    │   └──────────┘ └──────────┘   │
                    └───────────────────────────────┘
```

### Why MedGemma + RAG?

| Aspect | Benefit |
|--------|---------|
| **No training required** | MedGemma is already trained on medical images |
| **Community = your moat** | Doctor uploads → stored in disease vector DB → improves future diagnoses |
| **Explainable** | Shows which similar cases influenced the diagnosis |
| **Privacy-friendly** | Can run MedGemma locally |
| **Two-stage preserved** | Fast: top-K retrieval | Comprehensive: full database scan |

### Disease-Specific Vector Databases

Each disease has its **own vector database** containing:

```
Per Disease Database Entry:
├── Ultrasound Image(s)
│   └── Embedded via medical image encoder
├── Textual Symptom Description
│   └── Generated by MedGemma from the image
│   └── Embed via text encoder
└── Metadata
    ├── Trimester (1st, 2nd, 3rd)
    ├── Patient context (anonymized)
    ├── Diagnosis confidence
    └── Doctor/institution source
```

### Why Per-Disease Databases?

- **Isolation**: Disease-specific similarity search is more precise
- **Scalability**: New diseases = new database, no retraining
- **Relevance**: Query only relevant diseases (e.g., don't search cardiac if looking at brain)
- **Maintainability**: Update one disease's database without affecting others

### RAG Retrieval Flow

```
1. Doctor uploads ultrasound + context (trimester, parental params)

2. MedGemma generates symptom description:
   "Fetus shows increased nuchal translucency (3.2mm), absent nasal bone,
    cardiac anomaly consistent with AV canal defect..."

3. Query all disease vector DBs in parallel:
   - Embed input image + text
   - Retrieve top-K most similar symptom patterns per disease

4. Aggregation:
   - Combine similarity scores with trimester weights
   - Apply patient context as Bayesian priors
   - Calculate pondrated mean per disease

5. Return diagnosis:
   - Fast track: Top 3-5 probable diseases (immediate)
   - Comprehensive: Full disease list (background, async)
```

### No Training = Fast Hackaton Development

Traditional ML approach would require:
- Collecting thousands of labeled ultrasound images
- Training CNN/ViT models for each symptom
- Weeks/months of GPU time
- Medical expertise for labeling

**Our approach requires:**
- MedGemma integration
- Vector database setup
- RAG retrieval + aggregation logic
- Sample data for demonstration

This makes the hackaton timeline achievable while maintaining a path to production quality through community data accumulation.

---

## Key Features

### 1. Equipment Standardization Layer

**Problem**: Different ultrasound machines produce different image formats, resolutions, and metadata structures. Building API integrations for each manufacturer is impractical.

**Solution**: A local standardization layer that:

- Accepts raw image exports from any equipment (via file upload, not API)
- Normalizes formats (DICOM, JPEG, PNG, proprietary formats)
- Applies image enhancement filters appropriate for medical imaging
- Extracts and validates metadata (gestational age, acquisition parameters)
- Handles the 3 standard ultrasound timing windows

**Philosophy**: No vendor API dependencies. The app adapts to the equipment, not the other way around.

### 2. Trimester-Aware Diagnosis

Diseases manifest differently across trimesters. Our system weights symptom probability based on **when** the ultrasound was performed.

| Trimester | Timing | Typical Assessments |
|-----------|--------|--------------------|
| **1st** | 11–13+6 weeks | Nuchal translucency (NT), dating, multiple pregnancies, early structural anomalies |
| **2nd** | 22–24 weeks | Full morphological scan — brain, spine, heart, kidneys, limbs, sex determination |
| **3rd** | 32–34 weeks | Growth, fetal wellbeing, position, placenta location |

**Weighting System**: Each disease-symptom relationship has trimester-specific weights. For example:

```
Down Syndrome (Trisomy 21):
├── 1st Trimester:
│   ├── Increased NT (nuchal translucency): weight 0.85
│   ├── Absent nasal bone: weight 0.70
│   └── Heart abnormalities (early): weight 0.50
├── 2nd Trimester:
│   ├── Cardiac anomalies: weight 0.90
│   ├── Short femur length: weight 0.60
│   └── Duodenal atresia: weight 0.40
└── 3rd Trimester:
    └── Growth restriction: weight 0.55
```

### 3. Two-Stage Inference Engine

To balance speed, cost, and comprehensiveness:

#### Stage 1: Fast Probable Diseases (Immediate)

- Runs instantly upon image upload
- Analyzes only the most critical, highest-probability diseases
- Designed to **rule out** or **confirm** urgent cases
- Returns results within seconds
- Low computational cost

#### Stage 2: Comprehensive Scan (Background)

- Runs in the background after initial results
- Analyzes ALL diseases in the knowledge base
- More thorough symptom pattern matching
- May run on batched infrastructure to reduce costs
- Doctor receives comprehensive report asynchronously
- Useful for catching rare diseases or unusual presentations

### 4. Community Learning Platform

A critical differentiator — doctors contribute to collective intelligence:

#### Diagnosed Case Upload

- Doctor uploads ultrasound images + confirmed diagnosis
- Helps the model learn from real, validated cases
- Immediate improvement in diagnostic accuracy for similar presentations

#### Undiagnosed Case Upload (False Negative Feedback)

- Doctor uploads images where disease was NOT detected prenatally
- Child is born with a condition that was missed
- **This is the most valuable data for model improvement**
- Allows the system to learn from its mistakes

#### Discovery Mode

- System detects unusual patterns that don't match known diseases
- Flags potential NEW disease presentations
- Enables discovery of conditions not previously associated with ultrasound markers
- Community validation process for suspected new patterns

#### Gamification & Recognition

- Contributors see their impact score (cases helped, diseases discovered)
- Institutions can benchmark their diagnostic rates
- Encourages participation without monetary incentives

### 5. Risk Contextualization

Beyond images, the system incorporates patient context to adjust probabilities:

| Parameter | Influence |
|-----------|-----------|
| **Maternal Age** | >35 increases risk for chromosomal abnormalities |
| **Paternal Age** | >45 associated with new genetic mutations |
| **Family History** | Known hereditary conditions increase prior probability |
| **Previous Pregnancies** | History of chromosomal issues |
| **Ethnicity** | Some diseases more prevalent in specific populations |
| **IVF/Conception Method** | Higher twin/multiple pregnancy rates |

These parameters act as **Bayesian priors** — they adjust the baseline probability before the AI even analyzes the image.

---

## French Prenatal Ultrasound Context

In France, **3 ultrasound scans are recommended** for a normal pregnancy, all 100% covered by the French national health insurance (*Assurance Maladie*).

### The 3 Standard Ultrasounds

| Scan | Timing | Key Assessments |
|------|--------|-----------------|
| **1st Trimester** (Dating Scan) | 11–13+6 weeks | Pregnancy dating, nuchal translucency (NT) measurement for Down syndrome screening, multiple pregnancy detection |
| **2nd Trimester** (Morphology Scan) | 22–24 weeks (~5 months) | Complete organ examination — brain, spine, heart, kidneys, limbs. Sex determination possible. |
| **3rd Trimester** (Growth/Fetal Wellbeing) | 32–34 weeks (~7-8 months) | Baby position, placenta location, fetal vitality, growth assessment |

### Additional Context

- An **early dating ultrasound** (before 11 weeks) is optional but recommended by France's HAS (*Haute Autorité de Santé*)
- Additional ultrasounds can be prescribed if medically needed
- Exam duration: **15 to 30 minutes**
- Completely painless and safe — no radiation, uses sound waves

---

## Medical Context: Disease Detection Methods

### Non-Invasive Screening Methods

| Method | Description | Timing | Accuracy |
|--------|-------------|--------|----------|
| **Ultrasound (Echography)** | Structural abnormality detection, NT measurement | Any trimester | Variable by operator |
| **Cell-free DNA Test (cfDNA / NIPT)** | Analyzes fetal DNA in maternal blood | From week 10 | >99% for Trisomy 21 |
| **Serum Marker Screening** | Blood test for fetal substances | 10–20 weeks | ~85% detection rate |

### Invasive Diagnostic Tests

| Method | Description | Risk | Use Case |
|--------|-------------|------|----------|
| **Amniocentesis** | Needle extraction of amniotic fluid | ~0.5-1% miscarriage | Confirm suspected chromosomal issues |
| **Chorionic Villus Sampling (CVS)** | Placental tissue biopsy | ~0.5-1% miscarriage | Earlier confirmation (10-13 weeks) |
| **Cordocentesis** | Fetal blood from umbilical cord | Higher risk | Rare, specialized cases |
| **Preimplantation Genetic Testing (PGT)** | IVF embryo biopsy before transfer | IVF cycle dependent | Pre-conception, known genetic risks |

### Our Position

PrenatalAI aims to **reduce unnecessary invasive procedures** by providing better non-invasive screening through AI. When the AI probability is low, invasive procedures can be avoided. When the AI probability is high, invasive procedures can be targeted more precisely.

---

## Technology Philosophy

### No API Dependencies for Medical Equipment

**Problem**: Medical equipment manufacturers (GE, Philips, Siemens, etc.) have proprietary systems. Building and maintaining API integrations is:

- Expensive
- Time-consuming
- Fragile (vendor lock-in)
- Impossible for older equipment

**Our Approach**: The app accepts file uploads in standardized medical formats (DICOM, JPEG, PNG). This approach:

- Works with ANY equipment that can export images
- No vendor approval processes
- No API maintenance burden
- Accessible to resource-limited settings

### No-Training AI with MedGemma

**Traditional ML approach problems**:
- Requires thousands of labeled medical images
- Training takes weeks/months with GPU resources
- Needs medical experts for labeling
- Model updates require full retraining

**Our approach with MedGemma + RAG**:
- MedGemma already trained on medical imaging (no training needed)
- Community cases serve as "training data" in vector databases
- New cases improve retrieval quality instantly
- No GPU cluster required for development

### Privacy-First Architecture

- MedGemma can run locally (no cloud dependency)
- Patient data never leaves the doctor's control without explicit consent
- Community uploads are anonymized before sharing
- GDPR-compliant data handling
- Vector databases can be hosted on-premise

### Explainable AI

- Every diagnosis shows which similar community cases were retrieved
- MedGemma generates textual symptom descriptions (readable reasoning)
- Similarity scores visible per retrieved case
- Trimester weights and patient context factors disclosed
- Audit trails for medical liability

---

## Vision & Goals

### For This Hackathon

- [ ] Integrate MedGemma for symptom extraction from ultrasound images
- [ ] Set up per-disease vector databases (ChromaDB/Qdrant)
- [ ] Implement RAG retrieval with multi-modal search (images + text)
- [ ] Build trimester-aware aggregation layer with patient context
- [ ] Demonstrate two-stage inference (fast + comprehensive)
- [ ] Create mock community upload flow

### Long-Term Vision

- [ ] Validated medical device (CE marking, FDA clearance)
- [ ] Partnership with hospitals for clinical validation
- [ ] Integration with hospital PACS systems
- [ ] Discovery of new ultrasound markers for unknown diseases
- [ ] Global community of contributing physicians
- [ ] Reduction in unnecessary invasive procedures worldwide

---

## Project Status

**Current Phase**: Brainstorming & Architecture Definition

This document represents the initial vision and design decisions. The project is being developed as part of a Hackaton.

---

## Contributing

This project is in early development. If you're interested in contributing:

- Medical professionals: Share your expertise on disease presentations and ultrasound markers
- ML/AI engineers: Help build MedGemma integration and vector search
- Developers: Build the platform, APIs, and community features
- Healthcare UX designers: Help design the doctor interface

---

## Technology Stack

| Component | Technology | Role |
|-----------|------------|------|
| **Vision-Language AI** | MedGemma (Google DeepMind) | Symptom extraction from ultrasounds |
| **Vector Database** | Qdrant / ChromaDB | Per-disease symptom storage |
| **Embedding Models** | MedGemma encoder / BiomedCLIP | Multi-modal vectorization |
| **Backend** | Python (FastAPI) | API layer |
| **Frontend** | React / Next.js | Doctor interface |
| **Storage** | PostgreSQL + S3 | Metadata + image storage |

---

*Last updated: 2026-04-18*
*Project: AndsXMit Hackaton*
