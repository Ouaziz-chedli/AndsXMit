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
8. [Risks & Concerns](#risks--concerns)
9. [Vision & Goals](#vision--goals)
10. [Technology Stack](#technology-stack)

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
│   Ultrasound Image(s) + Current Trimester                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SYMPTOM EXTRACTION (MedGemma)                     │
│   AI Input: Ultrasound image ONLY                                     │
│   AI Output: Structured textual symptom description                   │
│   (Trimester context used only to select which vector DB to query)  │
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
| **AI scope limited** | MedGemma handles symptom extraction only; all contextual factors are algorithmic |
| **Community = your moat** | Doctor uploads → stored in disease vector DB → improves future diagnoses |
| **Explainable** | Shows which similar cases influenced the diagnosis |
| **Privacy-friendly** | Can run MedGemma locally |
| **Two-stage preserved** | Fast: top-K retrieval | Comprehensive: full database scan |

### Disease-Specific Vector Databases

Each disease has its **own vector database** containing **both positive (diseased) and negative (healthy/normal) examples** organized by trimester:

```
Per Disease Database (e.g., Down Syndrome):

├── 1st Trimester
│   ├── POSITIVE (Diseased)
│   │   ├── Ultrasound Images (confirmed Down Syndrome)
│   │   ├── Text: "NT 3.5mm, absent nasal bone, cardiac anomaly..."
│   │   └── Embeddings (image + text)
│   └── NEGATIVE (Healthy/Normal)
│       ├── Ultrasound Images (confirmed healthy)
│       ├── Text: "Normal NT 1.8mm, nasal bone present, normal heart"
│       └── Embeddings (image + text)
│
├── 2nd Trimester
│   ├── POSITIVE (Diseased)
│   │   ├── Images (cardiac defects, short femur, duodenal atresia)
│   │   └── Text: Symptom descriptions
│   └── NEGATIVE (Healthy/Normal)
│       ├── Images (normal organ morphology)
│       └── Text: "Normal cardiac chambers, normal femur length"
│
└── 3rd Trimester
    ├── POSITIVE (Diseased)
    │   ├── Images (growth restriction, other late markers)
    │   └── Text: Symptom descriptions
    └── NEGATIVE (Healthy/Normal)
        ├── Images (normal growth, normal wellbeing)
        └── Text: "Normal growth parameters, normal placenta"
```

### Why Healthy + Diseased Per Trimester?

| Aspect | Benefit |
|--------|---------|
| **Direct comparison** | System learns what disease AND normal look like |
| **Trimester-specific** | Normal measurements vary by trimester (NT in 1st ≠ growth in 3rd) |
| **Probability scoring** | `disease_similarity - normal_similarity = probability` |
| **False positive reduction** | Healthy examples prevent over-diagnosis |
| **Explainable** | Shows which normal cases matched → doctor reassurance |

### Scoring Logic

```
Diagnosis for input image:

1. Embed image + symptom text (via MedGemma encoder)

2. Retrieve top-K from disease DB:
   - K/2 most similar POSITIVE (diseased) cases
   - K/2 most similar NEGATIVE (healthy) cases

3. Calculate probability:
   score = avg(positive_similarities) - avg(negative_similarities) × trimester_weight

4. If score > threshold → Disease probable
   If score < threshold → Likely normal
```

### Aggregation Layer

The aggregation layer combines all signals into a final diagnosis probability:

#### Inputs to Aggregation

```
┌─────────────────────────────────────────────────────────────┐
│                      AGGREGATION LAYER                       │
│  (Algorithmic processing - NOT handled by AI)              │
│                                                             │
│  1. Per-Disease Similarity Scores (from vector search)       │
│     ├── Disease A: {positive_sim: 0.85, negative_sim: 0.30} │
│     ├── Disease B: {positive_sim: 0.60, negative_sim: 0.55} │
│     └── Disease N: ...                                       │
│                                                             │
│  2. Trimester Context (ALGORITHMIC)                         │
│     └── Which trimester weight profile to apply               │
│                                                             │
│  3. Patient Context - ALL ALGORITHMIC (Bayesian Priors)     │
│     ├── Maternal age: 38 → multiplier for chromosomal        │
│     ├── Family history: Down Syndrome → disease-specific boost│
│     ├── Genetic history: hereditary conditions               │
│     ├── Previous pregnancies: outcome history                 │
│     ├── Ethnicity: population-based priors                   │
│     └── IVF/Conception method                                │
└─────────────────────────────────────────────────────────────┘
```

**Key Principle**: MedGemma sees ONLY the ultrasound image. All contextual factors (age, genetics, history) are processed algorithmically in the aggregation layer, not by the AI model.

#### Step-by-Step Aggregation

**Step 1: Per-Disease Raw Score**

```
disease_score = avg(positive_similarities) - avg(negative_similarities)

Example:
  positive_sims = [0.85, 0.78, 0.82]  # top-K disease matches
  negative_sims = [0.30, 0.25, 0.35]  # top-K normal matches

  raw_score = mean(positive_sims) - mean(negative_sims)
           = 0.82 - 0.30 = 0.52
```

**Step 2: Apply Trimester Weights**

```
trimester_weights = {
    "1st":  {"Down Syndrome": 0.85, "Cardiac": 0.50, ...},
    "2nd":  {"Down Syndrome": 0.75, "Cardiac": 0.90, ...},
    "3rd":  {"Down Syndrome": 0.40, "Cardiac": 0.60, ...}
}

weighted_score = raw_score × trimester_weight[disease]
               = 0.52 × 0.85 = 0.44
```

**Step 3: Apply Patient Context Priors (Bayesian)**

```
prior_multipliers = {
    "maternal_age_38": {"chromosomal": 1.5, "cardiac": 1.1},
    "family_history_ds": {"Down Syndrome": 2.0, ...},
    "previous_chromosomal": {"chromosomal": 1.8, ...}
}

final_disease_score = weighted_score × prior_multiplier
                    = 0.44 × 1.5 = 0.66
```

**Dynamic Threshold Learning**: Instead of fixed thresholds (e.g., "age > 35"), the system learns optimal biomarker thresholds from community cases with confirmed outcomes. When enough data accumulates, the system discovers that age > 32.5 combined with low PAPP-A is more predictive than age alone — and updates thresholds automatically.

**Step 4: Symptom Overlap Handling**

When one symptom suggests multiple diseases:

```
# Example: "Cardiac anomaly" appears in multiple diseases
Symptom "cardiac_AV_canal_defect":
├── Down Syndrome:   weight 0.80
├── AVSD:            weight 0.90
└── Noonan Syndrome: weight 0.60

# Score distributed proportionally
total = 0.80 + 0.90 + 0.60 = 2.30

Down Syndrome:  0.66 × (0.80/2.30) = 0.23
AVSD:           0.66 × (0.90/2.30) = 0.26
Noonan:         0.66 × (0.60/2.30) = 0.17
```

#### Final Output

```
| Disease         | Raw Score | Trimester | Prior | Final |
|-----------------|-----------|-----------|-------|-------|
| Down Syndrome   | 0.52      | ×0.85     | ×1.5  | 0.66  |
| Edwards (T18)   | 0.45      | ×0.80     | ×1.3  | 0.47  |
| Patau (T13)     | 0.38      | ×0.75     | ×1.2  | 0.34  |
| Cardiac Defect  | 0.55      | ×0.90     | ×1.0  | 0.50  |
| Normal          | 0.70      | ×1.00     | ×1.0  | 0.70  |
```

#### Fast Track vs Comprehensive

| Stage | Aggregation Scope | Processing |
|-------|-------------------|------------|
| **Fast Track** | Top 5 most probable diseases | Synchronous, < 1 second |
| **Comprehensive** | All diseases in knowledge base | Background job, async |

### Why Per-Disease Databases?

- **Isolation**: Disease-specific similarity search is more precise
- **Scalability**: New diseases = new database, no retraining
- **Relevance**: Query only relevant diseases (e.g., don't search cardiac if looking at brain)
- **Maintainability**: Update one disease's database without affecting others

### RAG Retrieval Flow

```
1. Doctor uploads:
   - Ultrasound image(s) for current trimester
   - Patient context (age, genetics, history) → goes to ALGORITHMIC layer

2. MedGemma processes image ONLY:
   "Fetus shows increased nuchal translucency (3.2mm), absent nasal bone,
    cardiac anomaly consistent with AV canal defect..."

3. Query disease vector DBs (trimester-specific):
   - Embed input image
   - Retrieve top-K most similar symptom patterns per disease

4. Aggregation (ALGORITHMIC - not AI):
   - Combine similarity scores with trimester weights
   - Apply patient context (age, genetics, history) as Bayesian priors
   - Calculate pondrated mean per disease

5. Return diagnosis:
   - Fast track: Top 3-5 probable diseases (immediate)
   - Comprehensive: Full disease list (background, async)
```

**Important**: MedGemma does NOT receive patient context. The AI only sees the ultrasound image. All contextual factors (maternal age, genetic history, etc.) are processed algorithmically.

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

### 6. Adaptive Threshold Learning

Traditional medicine uses fixed thresholds (e.g., "PAPP-A < 0.5 MoM = high risk") derived from historical studies. **Our system learns dynamic thresholds from community data** — discovering which parameter values actually predict disease in real-world cases.

#### The Problem with Fixed Thresholds

- Thresholds are often set conservatively (to minimize false negatives)
- They don't adapt to population differences
- They can't discover new correlations between biomarkers and disease

#### Our Solution: Outcome-Based Threshold Discovery

```
1. Collect community cases with:
   - Patient biomarkers (age, PAPP-A, HCG, etc.)
   - Confirmed pregnancy outcome (diseased vs healthy)

2. For each parameter, the system discovers:
   - Optimal threshold: value that best separates diseased from healthy
   - Confidence band: range where threshold is statistically valid
   - Interaction effects: how parameters combine (e.g., age + PAPP-A together)

3. Example learned thresholds:
   - Maternal age > 32.5 (not 35!) + low PAPP-A → higher risk than either alone
   - HCG doublet rate > 1.8x baseline at week 10 → correlation with chromosomal
   - Combined biomarker panels outperform single markers

4. Update continuously as new confirmed cases are uploaded
```

#### Dynamic vs Fixed Thresholds

| Aspect | Fixed Thresholds | Adaptive Learning |
|--------|------------------|-------------------|
| **Source** | Historical studies | Community outcome data |
| **Update frequency** | Static | Continuous |
| **Population adaptation** | None | Cohort-specific |
| **Interaction detection** | Manual | Automated |
| **False positive rate** | High (conservative) | Optimized per use case |

#### Threshold Learning Process

```
┌─────────────────────────────────────────────────────────────┐
│                  THRESHOLD LEARNING PIPELINE                 │
│                                                             │
│  1. DATA COLLECTION                                          │
│     └── Confirmed outcomes (diseased/healthy) + biomarkers   │
│                                                             │
│  2. FEATURE ANALYSIS                                         │
│     └── Age, PAPP-A, HCG, NT, combinations                 │
│                                                             │
│  3. OPTIMAL THRESHOLD DISCOVERY                              │
│     └── ML model finds best separation points              │
│     └── Validates against holdout cases                     │
│                                                             │
│  4. CONFIDENCE SCORING                                       │
│     └── How reliable is this threshold?                    │
│     └── Based on sample size + statistical significance    │
│                                                             │
│  5. DEPLOYMENT TO AGGREGATION LAYER                          │
│     └── Dynamic thresholds replace static rules             │
│     └── Doctor sees: "Learned threshold: 32.5yo (vs 35)"    │
└─────────────────────────────────────────────────────────────┘
```

#### Discovery Bonus: New Diagnostic Correlations

A powerful side effect of threshold learning: **the system can discover that parameters previously thought unrelated to ultrasound diseases actually ARE correlated**.

```
Example:
- Input: Patient age 38, PAPP-A 0.3 MoM, HCG 1.9 MoM
- Discovery: These three markers together predict cardiac defect
- Validation: 47 community cases confirm pattern
- Result: New non-ultrasound predictor for cardiac disease!
```

This transforms the platform from **diagnosing what we know** to **discovering what we don't yet know**.

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

## Risks & Concerns

### ⚠️ Known Risks

| Risk | Severity | Issue |
|------|----------|-------|
| **MedGemma trained on radiology, not ultrasound** | **HIGH** | MedGemma was trained on CT, MRI, chest X-rays. Ultrasound has different image characteristics (noise, angles, artifacts). May underperform on prenatal images. |
| **Score ≠ calibrated probability** | **HIGH** | A score of 0.66 doesn't mean "66% chance of disease." No discussion of threshold calibration. In medicine, calibrated probabilities are essential for clinical decisions. |
| **Vector similarity ≠ diagnosis** | **MEDIUM** | Embedding similarity measures visual resemblance, not medical significance. Subtle markers that are critical for diagnosis may be lost in embedding space. |
| **Bootstrapping problem** | **MEDIUM** | Need data to be useful, but need to be useful to attract data. Community platform starts empty. |
| **False negatives = missed diagnosis** | **HIGH** | Medical context — a miss can have serious consequences. System needs validated sensitivity/specificity before clinical use. |
| **Latency** | **LOW** | Multiple vector DB queries + MedGemma inference — may be slow without optimization. |

### 🔧 Recommended Mitigations

1. **Test MedGemma on ultrasound first** — Run a quick experiment before committing. If it fails on ultrasound, the whole architecture needs revision.

2. **Calibrate probabilities** — Use a validation dataset to convert similarity scores to real probabilities (e.g., "score 0.6 = 73% accuracy").

3. **Add uncertainty quantification** — Instead of a single score, show confidence intervals.

4. **Add "Uncertain" category** — Cases where neither disease nor normal match well → flag for doctor review.

5. **Medical supervision required** — System should explicitly say "AI-assisted, not AI-diagnosis."

### 📊 Viability Assessment

| For Hackaton | For Production |
|--------------|---------------|
| **Viable as prototype/demo** | **Needs significant validation** |

The architecture is well-designed conceptually. The main risk is MedGemma's applicability to ultrasound — this needs empirical testing. If MedGemma works on ultrasounds, the approach is solid. If not, consider alternative vision-language models (e.g., BiomedCLIP, or a model specifically trained on ultrasound).

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
- [ ] **Learned biomarker thresholds** from community outcome data
- [ ] Global community of contributing physicians
- [ ] Reduction in unnecessary invasive procedures worldwide

### Data Strategy

#### Phase 1: Hackaton (Current)
- **Data sources**: Publicly accessible medical datasets (e.g., Kaggle ultrasound datasets, research publications with sample images)
- **Mock data**: Synthetic/mock cases to demonstrate architecture
- **Goal**: Prove the concept and architecture works

#### Phase 2: Certification & Clinical Trials
- **Objective**: Achieve regulatory clearance (CE marking in Europe, FDA clearance in US)
- **Clinical trials**: Partner with hospitals to validate diagnostic accuracy
- **Data access**: Certified medical institutions contribute anonymized cases
- **Funding**: Clinical trials funded through:
  - Research grants (EU Horizon programs, national health research funds)
  - Hospital partnerships (in-kind contribution)
  - Venture capital (post-prototype)

#### Phase 3: Community Scaling
- **Certified users**: Hospitals and clinics upload anonymized cases
- **Quality control**: Cases validated before entering community database
- **Network effect**: More users → better accuracy → more users
- **Data ownership**: Contributors retain ownership; licensing model for use

### Regulatory & Certification Path

#### CE Marking (Europe)
1. **Classify device**: Software as Medical Device (SaMD) — likely Class IIa or IIb
2. **Conformity assessment**: Meet MDR (Medical Device Regulation) requirements
3. **Clinical evaluation**: Demonstrate safety and performance
4. **Post-market surveillance**: Ongoing monitoring after deployment

#### FDA Clearance (USA)
1. **510(k) submission**: Demonstrate substantial equivalence to predicate device
2. **De novo pathway**: For novel devices without predicate
3. **Clinical studies**: Required for higher-risk classifications
4. **Quality System**: Comply with 21 CFR Part 820

#### Funding Clinical Trials
| Source | Type | Notes |
|--------|------|-------|
| **EU Research Grants** | Non-dilutive | Horizon Europe, EIC Accelerator |
| **National Health Institutes** | Non-dilutive | ANR (France), NHS (UK), NIH (US) |
| **Hospital Partnerships** | In-kind | Data contribution + trial infrastructure |
| **Venture Capital** | Dilutive | Post-prototype, for scaling |
| **Strategic Investors** | Dilutive | Medical device companies, health insurers |

---

## Project Status

**Current Phase**: Brainstorming & Architecture Definition

This document represents the initial vision and design decisions. The project is being developed as part of the **AndsXMit Hackaton**.

### What's Defined
- ✅ Core AI architecture (MedGemma + RAG)
- ✅ Per-disease vector database structure
- ✅ Aggregation layer logic
- ✅ Two-stage inference approach
- ✅ Data strategy (phased)
- ✅ Regulatory path (CE/FDA)

### What's Needed
- 🔲 MedGemma integration testing with ultrasound images
- 🔲 Vector database implementation
- 🔲 Threshold learning model (adaptive biomarker thresholds)
- 🔲 Prototype UI/UX
- 🔲 Mock community upload flow
- 🔲 Clinical partnership discussions

---

## Contributing

This project is in early development. If you're interested in contributing:

- **Medical professionals**: Share your expertise on disease presentations and ultrasound markers
- **ML/AI engineers**: Help build MedGemma integration and vector search
- **Developers**: Build the platform, APIs, and community features
- **Healthcare UX designers**: Help design the doctor interface
- **Data contributors** (future): Certified medical institutions for anonymized case uploads

### How You Can Help Now

1. **Spread the word** about the project
2. **Identify** publicly available ultrasound datasets
3. **Connect** us with hospitals or research institutions
4. **Review** our architecture for medical accuracy

---

## Technology Stack

| Component | Technology | Role |
|-----------|------------|------|
| **Vision-Language AI** | MedGemma (Google DeepMind) | Symptom extraction from ultrasounds |
| **Vector Database** | Qdrant / ChromaDB | Per-disease symptom storage |
| **Embedding Models** | MedGemma encoder / BiomedCLIP | Multi-modal vectorization |
| **Threshold Learning** | Scikit-learn / XGBoost | Dynamic biomarker threshold discovery |
| **Backend** | Python (FastAPI) | API layer |
| **Frontend** | React / Next.js | Doctor interface |
| **Storage** | PostgreSQL + S3 | Metadata + image storage |

---

*Last updated: 2026-04-18*
*Project: AndsXMit Hackaton*
