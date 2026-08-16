# FedRetina

**Privacy-Preserving Federated Diabetic Retinopathy Grading with Uncertainty Quantification and Grad-CAM++ Explainability**

FedRetina is a research prototype that grades diabetic retinopathy (DR) severity from retinal fundus images using **Federated Learning** (so patient images never leave the hospital), **Differential Privacy** (a mathematical guarantee that no single patient's data can be reconstructed from shared model weights), **Monte Carlo Dropout** (to flag predictions the model is unsure about), and **Grad-CAM++** (to show *why* the model made a prediction, via a lesion-level heatmap).

> Built as a BE Major Project — Department of Computer Engineering, Terna Engineering College.

---

## Table of contents

- [Why this project](#why-this-project)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [Backend setup](#backend-setup)
- [Frontend setup](#frontend-setup)
- [Datasets](#datasets)
- [Evaluation metrics](#evaluation-metrics)
- [Roadmap](#roadmap)
- [References](#references)
- [License](#license)

---

## Why this project

Diabetic Retinopathy affects 103M+ people worldwide and is a leading cause of preventable blindness. India has the world's second-largest diabetic population but a severe shortage of ophthalmologists, especially in rural areas. Deep learning can automate DR screening, but:

1. **Centralised training violates privacy law.** Pooling patient fundus images on one server conflicts with India's Digital Personal Data Protection (DPDP) Act 2023.
2. **Existing federated DR systems are clinically unsafe.** They provide no way to flag low-confidence predictions and no visual explanation clinicians can audit.

FedRetina addresses both problems in one pipeline.

## Architecture

```
 Hospital Node 1 ─┐
 Hospital Node 2 ─┼──▶ Differential Privacy ──▶ Flower FL Server ──▶ Global Model
 Hospital Node 3 ─┘   (clip + Gaussian noise)     (FedAvg, R=50)         │
        ▲                                                                 │
        └─────────────────────── updated global model ────────────────────┤
                                                                            ▼
                                                     ┌──────────────────────────────┐
                                                     │   MC Dropout (T=30 passes)    │
                                                     │   → predicted grade +         │
                                                     │     uncertainty score         │
                                                     └───────────────┬──────────────┘
                                                                     ▼
                                                     ┌──────────────────────────────┐
                                                     │   Grad-CAM++ heatmap          │
                                                     └───────────────┬──────────────┘
                                                                     ▼
                                                     React Clinician Dashboard
                                                     (grade, confidence, flag, heatmap)
                                                     FastAPI + MongoDB backend
```

Each hospital node trains an EfficientNetB3 model locally on its own partition of fundus images, clips and noises its gradients (ε=0.5, δ=10⁻⁵), and sends only the noised weights to the central Flower server, which aggregates them with FedAvg. The resulting global model is used for inference with MC Dropout uncertainty scoring and Grad-CAM++ explainability, surfaced through a clinician-facing dashboard.

## Tech stack

| Layer | Technology |
|---|---|
| Model | PyTorch, EfficientNetB3 (`timm` or `torchvision`) |
| Federated learning | [Flower (flwr)](https://flower.ai) |
| Differential privacy | [Opacus](https://opacus.ai) |
| Explainability | [pytorch-grad-cam](https://github.com/jacobgil/pytorch-grad-cam) |
| Backend API | FastAPI, Uvicorn |
| Database | MongoDB (Motor / PyMongo) |
| Frontend | React.js, Chart.js / Recharts |
| Datasets | APTOS 2019, IDRiD, EyePACS |

## Repository structure

```
fedretina/
├── backend/
│   ├── app/                 # FastAPI application (routes, schemas, db)
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── predict.py
│   │   │   └── patients.py
│   │   ├── db.py
│   │   └── schemas.py
│   ├── fl/                  # Federated learning (Flower client + server)
│   │   ├── server_app.py
│   │   ├── client_app.py
│   │   └── strategy.py
│   ├── model/                # Model architecture, training, inference
│   │   ├── efficientnet_model.py
│   │   ├── mc_dropout.py
│   │   └── gradcam_explainer.py
│   ├── data/                 # Preprocessing utilities
│   │   └── preprocessing.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadPanel.jsx
│   │   │   ├── HeatmapViewer.jsx
│   │   │   ├── ResultCards.jsx
│   │   │   └── PredictionsTable.jsx
│   │   ├── App.jsx
│   │   └── api.js
│   └── package.json
├── data/
│   └── sample/                # Small sample CSVs matching APTOS 2019 format
├── docs/
│   ├── architecture.png
│   ├── dfd_level0.png
│   ├── dfd_level1.png
│   └── uml/
└── README.md
```

## Getting started

```bash
git clone https://github.com/<your-username>/fedretina.git
cd fedretina
```

You'll need Python 3.10+, Node.js 18+, and a local or Atlas MongoDB instance.

## Backend setup

### 1. Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

`requirements.txt` should include at minimum:

```
torch
torchvision
flwr[simulation]
opacus
grad-cam
fastapi
uvicorn[standard]
motor
pymongo
pydantic
pillow
numpy
pandas
scikit-learn
```

### 2. Configure MongoDB

Create a `.env` file in `backend/`:

```
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=fedretina
```

### 3. Run the federated training simulation

```bash
cd backend/fl
flwr run .          # launches the Flower simulation: 3 hospital nodes + server, R=50 rounds
```

This trains the global EfficientNetB3 model with DP-noised updates and saves the final weights to `backend/model/checkpoints/global_model.pt`.

### 4. Start the inference API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Key endpoints:

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/predict` | Upload a fundus image → returns grade, confidence, uncertainty score, referral flag, heatmap URL |
| `GET` | `/api/predictions` | List recent predictions from MongoDB |
| `GET` | `/api/predictions/{id}` | Fetch one prediction record |
| `GET` | `/api/health` | Health check |

Interactive API docs are auto-generated by FastAPI at `http://localhost:8000/docs`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The dashboard runs at `http://localhost:5173` (Vite) or `http://localhost:3000` (CRA) and talks to the backend at `http://localhost:8000` — set the base URL in `frontend/src/api.js`.

## Datasets

| Dataset | Images | Role |
|---|---|---|
| [APTOS 2019](https://www.kaggle.com/competitions/aptos2019-blindness-detection/data) | 3,662 | Primary training set, split across 3 simulated hospital nodes |
| [IDRiD](https://ieee-dataport.org/open-access/indian-diabetic-retinopathy-image-dataset-idrid) | 516 | India-specific cross-dataset validation |
| EyePACS (Kaggle subset) | 2,000 | Secondary generalisability test |

See `data/sample/train_sample.csv` for a small sample in the exact format of the APTOS 2019 `train.csv` (columns: `id_code`, `diagnosis`).

## Evaluation metrics

- **Quadratic Weighted Kappa (QWK)** — primary DR grading metric
- **Macro F1-score**
- **Expected Calibration Error (ECE)**
- **Negative Log-Likelihood (NLL)**
- **Privacy budget (ε, δ)** per training round

## Roadmap

- [ ] Asynchronous FL for hospitals with intermittent connectivity
- [ ] FedProx regularisation for severe non-IID data
- [ ] OCT imaging as a second modality
- [ ] Prospective clinical validation with ophthalmology departments

## References

1. McMahan et al., "Communication-efficient learning of deep networks from decentralized data" (FedAvg), AISTATS 2017.
2. Abadi et al., "Deep learning with differential privacy," ACM CCS 2016.
3. Gal & Ghahramani, "Dropout as a Bayesian approximation," ICML 2016.
4. Chattopadhay et al., "Grad-CAM++," IEEE WACV 2018.
5. Tan & Le, "EfficientNet," ICML 2019.
6. Porwal et al., "IDRiD," Data 2018.

Full reading list in `docs/`.

## License

MIT — see `LICENSE`. Datasets remain subject to their own licenses (Kaggle/APTOS, IEEE Dataport/IDRiD).
