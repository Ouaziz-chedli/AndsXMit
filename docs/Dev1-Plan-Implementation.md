# Dev1 - Plan d'Implémentation

**Responsabilité**: `image → MedGemma symptom extraction → ChromaDB vector search → scored results`

---

## Vue d'ensemble

Le Dev1 construit le pipeline AI/ML de base pour le diagnostic prénatal. L'objectif est de créer un système qui:

1. Extrait les symptômes des échographies via **MedGemma** (local uniquement)
2. Recherche des cas similaires via **ChromaDB** (vector store local)
3. Calcule des scores de risque avec des **priors biomédicaux** (b-hCG, PAPP-A, âge maternel)
4. Retourne des résultats classés par probabilité

**Contrainte clé**: Tout doit fonctionner **offline** dans Docker (auto-hébergement hospitalier).

---

## Phase 1: Fondations (Modèles Pydantic partagés)

Les modèles Pydantic définissent le contrat entre Dev1 et Dev2. À placer dans `backend/app/models/`.

### Fichiers à créer

| Fichier | Contenu | Utilité |
|---------|---------|---------|
| `models/diagnosis.py` | `DiagnosisQuery`, `DiagnosisResult` | API endpoints |
| `models/patient.py` | `PatientContext`, `PatientContextMoM` | Contexte patient avec biomarqueurs |
| `models/case.py` | `DiseaseCase`, `RetrievedCase` | Vector DB et résultats |

### Exemple de modèles clés

```python
class PatientContext(BaseModel):
    """
    Contexte de dépistage du 1er trimestre.
    Basé sur le protocole français NT-prenatal screening (11-14 semaines).

    Biomarqueurs clés:
    - b-hCG (IU/L) - beta human chorionic gonadotropin
    - PAPP-A (IU/L) - Pregnancy-associated plasma protein A
    - Age de la mère à l'accouchement
    - Âge gestationnel en semaines
    """
    b_hcg: float | None = None
    papp_a: float | None = None
    mother_age: int
    gestational_age_weeks: float
    previous_affected_pregnancy: bool = False

    def to_mom(self) -> "PatientContextMoM":
        """Convertit les valeurs brutes en MoM (Multiple of Median)."""
        MEDIAN_B_HCG = 50000.0  # IU/L
        MEDIAN_PAPP_A = 1500.0  # IU/L
        return PatientContextMoM(
            b_hcg_mom=self.b_hcg / MEDIAN_B_HCG if self.b_hcg else None,
            papp_a_mom=self.papp_a / MEDIAN_PAPP_A if self.papp_a else None,
            mother_age=self.mother_age,
            gestational_age_weeks=self.gestational_age_weeks,
            previous_affected_pregnancy=self.previous_affected_pregnancy,
        )
```

---

## Phase 2: Modules Core

### Structure des modules

```
backend/app/core/
├── medgemma.py          # Inférence MedGemma locale
├── vector_store.py      # Abstraction ChromaDB
├── scoring.py           # Calcul des scores bruts
├── aggregation.py       # Pondération par trimestre
├── priors.py            # Priors biomédicaux (b-hCG, PAPP-A)
└── image_processor.py   # Traitement DICOM/JPEG/PNG
```

### 1. `medgemma.py` - Extraction de symptômes

```python
async def extract_symptoms(image_bytes: bytes) -> SymptomDescription:
    """
    Analyse une image d'échographie et extrait les symptômes.

    MedGemma ne reçoit QUE l'image. Tout contexte patient
    est traité algorithmiquement dans la couche d'agrégation.
    """
    model = MedGemma.load_local()
    symptoms = model.analyze(image_bytes)
    return symptoms
```

### 2. `vector_store.py` - ChromaDB

```python
client = chromadb.PersistentClient(path="/data/vector_db")

async def search_disease(
    query_embedding: list[float],
    disease_id: str,
    trimester: str,
    top_k: int = 10
) -> list[RetrievedCase]:
    """
    Recherche les cas les plus similaires dans le vector store.
    Filtré par maladie et trimestre.
    """
    collection = client.get_collection(f"{disease_id}_{trimester}")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return parse_results(results)
```

### 3. `scoring.py` - Score brut

```python
def calculate_raw_score(
    positive_sims: list[float],
    negative_sims: list[float]
) -> float:
    """
    score = avg(positive_similarities) - avg(negative_similarities)
    """
    return mean(positive_sims) - mean(negative_sims)
```

### 4. `aggregation.py` - Pondération trimestre

```python
TRIMESTER_WEIGHTS = {
    "1st": {"down_syndrome": 0.85, "cardiac_defect": 0.50},
    "2nd": {"down_syndrome": 0.75, "cardiac_defect": 0.90},
    "3rd": {"down_syndrome": 0.40, "cardiac_defect": 0.60},
}

def aggregate_scores(raw_score: float, disease: str, trimester: str) -> float:
    return raw_score * TRIMESTER_WEIGHTS[trimester][disease]
```

### 5. `priors.py` - Priors biomédicaux

```python
def apply_priors(
    weighted_score: float,
    disease: str,
    context: PatientContext | PatientContextMoM,
) -> float:
    """
    Applique tous les priors pour obtenir la probabilité finale.

    Pour les maladies chromosomiques (Down, Edwards, Patau):
    - L'âge maternel est un facteur significatif
    - Les valeurs MoM de b-hCG et PAPP-A indiquent des motifs spécifiques
    """
    multiplier = 1.0

    # Âge maternel
    age_risk = calculate_age_risk(context.mother_age)
    if disease in ("down_syndrome", "edwards_syndrome", "patau_syndrome"):
        multiplier *= age_risk

    # Biomarqueurs
    if isinstance(context, PatientContextMoM):
        biomarker_risk = calculate_biomarker_risk(
            context.b_hcg_mom,
            context.papp_a_mom
        )
        if disease in ("down_syndrome", "edwards_syndrome", "patau_syndrome"):
            multiplier *= biomarker_risk

    # Grossesse antérieure affectée
    if context.previous_affected_pregnancy:
        multiplier *= 2.5

    return weighted_score * multiplier
```

---

## Phase 3: Données de Test

### Mock cases pour Down Syndrome

```python
# data/mock_cases/down_syndrome_1st.json
[
    {
        "case_id": "ds_pos_001",
        "disease_id": "down_syndrome",
        "trimester": "1st",
        "label": "positive",
        "symptom_text": "nt_3_5mm absent_nasal_bone",
        "gestational_age_weeks": 12.0,
        "b_hcg_mom": 2.1,      # Élevé (typique Down)
        "papp_a_mom": 0.48,     # Bas (typique Down)
    },
    {
        "case_id": "norm_001",
        "disease_id": "down_syndrome",
        "trimester": "1st",
        "label": "negative",
        "symptom_text": "normal_nt_1_8mm nasal_bone_present",
        "gestational_age_weeks": 12.0,
        "b_hcg_mom": 1.0,      # Normal
        "papp_a_mom": 1.0,     # Normal
    }
]
```

### Scripts

| Script | Fonction |
|--------|----------|
| `seed_mock_data.py` | Peuple ChromaDB avec les cases mock |
| `compute_embeddings.py` | Pré-calcule les embeddings avec MedGemma |

---

## Phase 4: Tests

```
backend/tests/
├── test_medgemma.py       # Tests extraction symptômes
├── test_vector_store.py   # Tests recherche vectorielle
├── test_scoring.py        # Tests calcul scores
├── test_aggregation.py    # Tests pondération
└── test_priors.py        # Tests priors biomédicaux
```

---

## MVP Priority (Ordre d'implémentation)

| Priorité | Tâche | Statut |
|----------|-------|--------|
| 1 | Créer les modèles Pydantic partagés | ⬜ |
| 2 | Implémenter `vector_store.py` (ChromaDB) | ⬜ |
| 3 | Implémenter `scoring.py` | ⬜ |
| 4 | Implémenter `aggregation.py` | ⬜ |
| 5 | Implémenter `priors.py` | ⬜ |
| 6 | Créer les mock cases | ⬜ |
| 7 | Implémenter `medgemma.py` (avec mock si modèle lent) | ⬜ |
| 8 | Écrire les tests unitaires | ⬜ |
| 9 | End-to-end: 1 maladie, 1 trimestre | ⬜ |

---

## Référence: Priors Biomédicaux

| Marqueur | Nom complet | Normal (MoM) | Pattern Down Syndrome |
|----------|-------------|--------------|----------------------|
| **b-hCG** | Beta hCG | ~1.0 MoM | Élevé (~2.0 MoM) |
| **PAPP-A** | PAPP-A | ~1.0 MoM | Bas (~0.5 MoM) |
| **NT** | Nuchal Translucency | <3.0mm | Élevé (>3.0mm) |

**MoM** = Multiple of Median (normalise selon l'âge gestationnel)

---

## Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Framework | FastAPI |
| Validation | Pydantic v2 |
| Vector DB | ChromaDB (embedded, PersistentClient) |
| AI | MedGemma (local) |
| Images | pydicom + Pillow |
| Tests | pytest |

---

## Déploiement

```bash
# Docker compose
docker compose up

# Un seul container avec:
# - Modèles MedGemma dans /data/models
# - ChromaDB embedded dans /data/vector_db
```

---

*Version: 1.0*
*Dernière mise à jour: 2026-04-18*
*Dev: Ali Bassim*
