# Product Requirements Document: AI-Powered Phishing Detection

## 1. Overview

The project will deliver a research-grade phishing detection system that classifies pasted email text and URLs as legitimate, spam, or phishing. The system will use Hugging Face Transformers with RoBERTa as the only fine-tuned model family to reduce training cost, memory usage, and implementation complexity.

The final deliverable is a client-server architecture featuring a Dockerized FastAPI REST backend for model serving and a Streamlit web frontend for user interaction. It can be developed in VS Code and trained with local or hosted compute.

## 2. Product Goals

- Detect phishing intent in email body text using a fine-tuned RoBERTa classifier.
- Detect malicious or phishing URLs using a fine-tuned RoBERTa URL classifier.
- Provide a secure, production-ready REST API (FastAPI) supporting single and batch inference with token-based authentication.
- Provide a Streamlit web interface acting as an API client for manual testing and bulk evaluation.
- Keep the implementation lightweight by removing BERT side-by-side comparison from the project scope.


## 3. Target Users

- Cybersecurity students or researchers evaluating transformer-based phishing detection.
- Security analysts who need a demo workflow for suspicious emails and links.
- Project supervisors reviewing a practical ML security build.

## 4. Core User Stories

| ID | User Story | Acceptance Criteria |
| --- | --- | --- |
| US-01 | As a user, I can paste an email body and get a verdict. | The app returns Legitimate, Spam, or Phishing with confidence. |
| US-02 | As a user, I can paste a URL and get a verdict. | The app returns Legitimate or Phishing with confidence. |
| US-03 | As a user, I can paste an email containing URLs. | The system intelligently routes the text or URL for classification. |
| US-04 | As a developer, I can fine-tune the email model from CSV data. | A command trains and saves `models/email-roberta`. |
| US-05 | As a developer, I can fine-tune the URL model from CSV data. | A command trains and saves `models/url-roberta`. |
| US-06 | As a developer, I can run the project in Docker. | `docker compose up --build` starts the Streamlit app. |
| US-07 | As a developer, I can work in VS Code. | `.vscode` and `.devcontainer` configuration are provided. |
| US-08 | As a developer or client, I can authenticate to the API. | The `/token` endpoint accepts credentials and returns a JWT. |
| US-09 | As a user, I can submit a batch of URLs/texts. | The system processes them in bulk and displays aggregate statistics. |

## 5. Dataset Requirements

The system integrates localized corpora, threat intelligence feeds, and remote datasets programmatically downloaded from Hugging Face, placed in the `data/raw/` directory.

### 5.1 Email Training Data

| Dataset Source | Path / Identifier | Labels | Purpose |
| --- | --- | --- | --- |
| **CEAS-08** | `Email Datasets/CEAS_08.csv` | Spam / Ham | Spam and legitimate email training |
| **Enron Corpus** | `Email Datasets/Enron.csv` | Ham | Legitimate corporate negative class |
| **Ling-Spam** | `Email Datasets/Ling.csv` | Spam / Ham | Spam and legitimate email baseline |
| **Nazario Phishing** | `Email Datasets/Nazario.csv`, `Nazario_5.csv` | Phishing | Phishing email examples |
| **Nigerian Fraud** | `Email Datasets/Nigerian_5.csv`, `Nigerian_Fraud.csv` | Phishing | Advance-fee fraud email corpus |
| **SpamAssassin** | `Email Datasets/SpamAssasin.csv` | Spam / Ham | Public spam corpus |
| **TREC 2005/06/07** | `Email Datasets/TREC_0*.csv` | Spam / Ham | Large spam track email corpora |
| **Hugging Face Hub** | `Gunjand07/email-spam-dataset` | Spam / Ham | Modern spam corpus |
| **Hugging Face Hub** | `SchoolP/Email_Spam_Dataset` | Spam / Ham | Supplemental email spam dataset |
| **Hugging Face Hub** | `pleasenotagain/sanct-classify-emailspam-dataset` | Spam / Ham | Supplemental email spam dataset |
| **Hugging Face Hub** | `SetFit/enron_spam` | Spam / Ham | Standard classification split of Enron |
| **Hugging Face Hub** | `Teddyha/phishing_benign_email_dataset` | Benign / Phishing | Phishing email examples |
| **Hugging Face Hub** | `luongnv89/phishing-email` | Benign / Phishing | Phishing email examples |
| **Hugging Face Hub** | `JinqiangDing/seven-phishing-email-datasets` | Benign / Phishing | Consolidated phishing dataset |
| **Hugging Face Hub** | `NatalieBob/phishing-email-dataset` | Benign / Phishing | Phishing email examples |
| **Hugging Face Hub** | `deevyanshu/phishing_detection` | Benign / Phishing | Phishing email examples |
| **Hugging Face Hub** | `shivahoody007/Phishing_Link_Pattern_Dataset` | Benign / Phishing | Phishing link pattern examples |

### 5.2 URL Training Data

| Dataset Source | Path / Identifier | Labels | Purpose |
| --- | --- | --- | --- |
| **Kaggle Malicious URLs** | `URL Datasets/Kaggle Malicious URLs (651k)/malicious_phish.csv` | Benign / Phishing / Malware / Defacement | Large 651k malicious URL dataset |
| **Tranco Top Domains** | `URL Datasets/Tranco ID 3Q25L. 1m/` | Benign | Top 1M benign baseline domains |
| **Hugging Face Hub** | `flwrlabs/fed-phishing-urls` | Benign / Phishing | Collaborative URL phishing dataset |
| **Hugging Face Hub** | `mahmoud0333/PhishingURLsANDBenignURLs` | Benign / Phishing | Balanced URL dataset |
| **Hugging Face Hub** | `pirocheto/phishing-url` | Benign / Phishing | Programmatic URL dataset |
| **PhishTank** | `PhishTank.csv` | Phishing | Active phishing links feed |
| **URLhaus** | `urlhaus_recent.csv` | Malware / Phishing | Threat intelligence malware links feed |
| **Majestic Million** | `majestic_million.csv` | Benign | Standard benign baseline domains |

### 5.3 Data Processing Rules

- **Deduplication**: Drop duplicates based on the exact raw input text (`text` for emails, `url` for URLs).
- **Train/Val/Test Splits**: Use stratified splits of 70% training, 15% validation, and 15% testing, preserving label distributions.
- **Label Mapping consistency**:
  - Email: `0=Legitimate` (mapped from ham, benign, safe), `1=Spam` (mapped from spam), `2=Phishing` (mapped from phishing, malware, fraud, nigerian).
  - URL: `0=Legitimate` (mapped from benign), `1=Phishing` (mapped from phishing, malware, defacement, spam, yes, valid).
- **Email Text Preprocessing**: Convert all text to lowercase. Strip HTML tags to extract plain text (using BeautifulSoup or fallback HTMLParser).
- **Email Dataset Balancing**: The full natural class distribution is retained without downsampling to preserve maximum training signal. After deduplication and label mapping, the combined email corpus totals **~8.2 million** unique samples.
- **URL Normalization**: Lowercase URL strings, ensure schema is prepended, decode percent-encoded characters, and strip known web tracking parameters (e.g. `utm_*`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`).
- **URL Dataset Balancing**: Legitimate URLs are randomly undersampled to match the size of the malicious class to prevent classifier bias, producing **1,449,471** balanced training records (~724,735 per class) from an unbalanced pool of ~2.87 million.
- **Excluded Datasets**: `it4lia/PhishingEmailCuratedDatasets_Cleaned` (metadata-only, no usable text column) and `ISCX-URL-2016` (feature-engineered CSV format, not raw URL strings) are explicitly excluded from the preprocessing pipeline.

## 6. Functional Requirements

| Requirement | Description | Priority |
| --- | --- | --- |
| FR-01 | Parse raw email text and clean HTML/noisy formatting. | Must |
| FR-02 | Extract embedded URLs from email text. | Must |
| FR-03 | Normalize URL strings before training and inference. | Must |
| FR-04 | Fine-tune RoBERTa for 3-class email classification. | Must |
| FR-05 | Fine-tune RoBERTa for 2-class URL classification. | Must |
| FR-06 | Intelligently route requests to URL or Email models based on content. | Must |
| FR-07 | Provide a Streamlit frontend client for manual testing. | Must |
| FR-08 | Provide Docker and VS Code setup files. | Must |
| FR-09 | Export evaluation metrics and confusion matrices. | Should |
| FR-10 | Add model explainability using Gradient Norm (Saliency) feature importances. | Must |
| FR-11 | Implement a FastAPI backend with single and batch inference routes. | Must |
| FR-12 | Implement JWT token-based authentication and payload size limits. | Must |
| FR-13 | Log single and batch predictions to an SQLite database history log. | Must |
| FR-14 | Protect API endpoints using IP-based request rate limiting. | Must |
| FR-15 | Provide a dashboard tab in the Streamlit UI to view, refresh, and clear prediction logs. | Must |

## 7. Model Requirements

The model library is Hugging Face Transformers. The only fine-tuned transformer model family is RoBERTa.

### 7.1 Email Classifier

- Base checkpoint: `roberta-base`
- Task: sequence classification
- Classes: Legitimate, Spam, Phishing
- Max sequence length: 512 tokens
- Loss: cross entropy, with class weights if imbalance is severe
- Output directory: `models/email-roberta`

### 7.2 URL Classifier

- Base checkpoint: `roberta-base`
- Task: sequence classification
- Classes: Legitimate, Phishing
- Max sequence length: 128 tokens
- Input: normalized URL string
- Output directory: `models/url-roberta`

### 7.3 Training Defaults

| Hyperparameter | Email Model Value | URL Model Value |
| --- | --- | --- |
| Base Checkpoint | `roberta-base` | `roberta-base` |
| Learning rate | 2e-5 | 2e-5 |
| Epochs | 4 | 4 |
| Train batch size | 8 | 32 |
| Eval batch size | 16 | 16 |
| Warmup ratio | 0.1 | 0.1 |
| Optimizer | AdamW | AdamW |
| Scheduler | Linear decay | Linear decay |
| Gradient accumulation | 2 | 1 |
| Weight decay | 0.01 | 0.01 |

## 8. Evaluation Requirements

Accuracy alone is not sufficient because phishing detection is security-sensitive and may be imbalanced.

### 8.1 Target Evaluation Metrics

| Metric | Target |
| --- | --- |
| Phishing precision | > 0.92 |
| Phishing recall | > 0.95 |
| Macro F1 | > 0.93 |
| False negative rate | < 5% |
| False positive rate | < 3% |

Evaluation must be reported separately for:
- Email-only classifier
- URL-only classifier
- Combined email plus URL pipeline

### 8.2 Actual Evaluation Results

The models were evaluated on their respective held-out test splits after the full pipeline rerun. The performance metrics are detailed below:

#### Email-Only Classifier (`models/email-roberta`)
- **Evaluation Set Size**: 36,206 samples (15% stratified hold-out)
- **Overall Accuracy**: 94%
- **Macro average F1-score**: 0.94
- **Per-Class Metrics**:

| Class | Precision | Recall | F1-Score | Support |
| --- | --- | --- | --- | --- |
| Legitimate | 0.98 | 0.99 | 0.99 | 12,068 |
| Spam | 0.97 | 0.85 | 0.91 | 12,069 |
| Phishing | 0.87 | 0.97 | 0.92 | 12,069 |

- **Confusion Matrix** (`[[TN, FP, FP], [FN, TP, FP], [FN, FP, TP]]`):
  - Legitimate: 11,962 correct / 59 → Spam / 47 → Phishing
  - Spam: 105 → Legitimate / 10,296 correct / 1,668 → Phishing
  - Phishing: 97 → Legitimate / 256 → Spam / 11,716 correct

#### URL-Only Classifier (`models/url-roberta`)
- **Evaluation Set Size**: 211,809 samples (15% stratified hold-out)
- **Overall Accuracy**: 96%
- **Macro average F1-score**: 0.96
- **Per-Class Metrics**:

| Class | Precision | Recall | F1-Score | Support |
| --- | --- | --- | --- | --- |
| Legitimate | 0.95 | 0.97 | 0.96 | 102,724 |
| Phishing | 0.97 | 0.95 | 0.96 | 109,085 |

- **Confusion Matrix**:
  - Legitimate: 99,846 correct / 2,878 → Phishing
  - Phishing: 4,940 → Legitimate / 104,145 correct

## 9. System Architecture

| Component | Technology | Responsibility |
| --- | --- | --- |
| Frontend UI | Streamlit | Input form, batch upload, prediction history logs, and REST API client |
| Backend API | FastAPI | Token auth, rate limiting, routing, JSON logging, model lifecycle |
| Database | SQLite (`data/predictions.db`) | Persistent logging of prediction history, supporting query and delete operations |
| Email preprocessing | Python, BeautifulSoup | Clean email text and extract URLs |
| URL preprocessing | urllib, tldextract-ready design | Normalize URLs and derive structural features |
| Email model | RoBERTa + Transformers | Email classification |
| URL model | RoBERTa + Transformers | URL classification |
| Container | Docker / Docker Compose | Reproducible setup for both API and UI |
| IDE | VS Code | Development and debugging |

## 10. Inference Flow

1. **Authentication**: User or programmatic client authenticates with the FastAPI backend (`/token` endpoint) to receive a JWT access token.
2. **Rate Limiting**: Custom `RateLimitingMiddleware` checks incoming request IP addresses. Clients are limited to 100 requests per 60 seconds, with excess requests rejected with an HTTP 429 Too Many Requests status code.
3. **Submission**: Client submits a single text or batch payload via Streamlit UI or direct API call, passing the JWT token.
4. **Payload Enforcer**: FastAPI middleware enforces maximum payload size limits (e.g. 5MB) and logs incoming requests.
5. **Intelligent Routing & Allowlist Bypass**:
   - The system checks if the trimmed input is a pure URL (no spaces, starts with `http://`, `https://`, or `www.`).
   - If it is a pure URL, it is routed exclusively to the URL classifier model.
   - If it contains text, it is treated as an email body. The system extracts any embedded URLs via regex. If URLs are found, they are sent to the URL model; the main text body is sent to the Email model.
   - An Enterprise Allowlist (`KNOWN_SAFE_DOMAINS`) is checked for URLs: if the domain is verified safe, it bypasses the model and returns a safe verdict with 99% confidence.
6. **Verdict Aggregation**:
   - **URL Precedence Rule**: If any extracted URL is classified as phishing with confidence >= 80%, the entire pipeline output is overridden and marked as "Phishing" immediately.
   - **Email Fallback Rule**: If URLs are safe or absent, the email classifier's output dictates the verdict (Legitimate, Spam, or Phishing).
   - **URL-only Fallback**: If no email text is provided but URLs are, the highest-confidence URL classification is returned.
   - **Unknown Fallback**: If neither valid text nor URLs are found, it returns "Unknown".
7. **Explainability Mapping**: If explainability is enabled, the system computes Gradient Norm (Saliency) feature importances for words in the input.
8. **Database Logging**: The system logs every prediction run to the local SQLite database (`data/predictions.db`), storing input content, prediction type, classification label, confidence level, boolean phishing flag, and reason text.
9. **Response rendering & History Querying**: FastAPI returns a structured JSON response, and the Streamlit client renders results, bar charts, metrics, and highlight overlays. Users can also view, refresh, and clear past scans on the "Prediction History" tab.

## 11. Repository Structure

| Path | Purpose |
| --- | --- |
| `backend/main.py` | FastAPI application entry point, lifespans, logging, and middlewares |
| `backend/api/auth.py` | FastAPI router for authentication and token generation |
| `backend/api/predict.py` | FastAPI router for single and batch predictions, including history retrieval and clearing |
| `backend/core/config.py` | Centralized system configurations (model paths, thresholds, safety allowlist, security keys) |
| `backend/core/database.py` | SQLite helper functions to initialize/log/retrieve/clear prediction history |
| `backend/core/inference.py` | Core model inference wrapper and gradient-based word explainability (saliency) handler |
| `backend/core/rate_limiter.py` | IP-based request rate limiting middleware |
| `backend/core/security.py` | JWT token decoding, password hashing, and user authentication utilities |
| `backend/schemas/predict.py` | Pydantic validation schemas for prediction requests, batch inputs, and response payloads |
| `frontend/streamlit_app.py` | Streamlit web client implementing input forms, batch file uploads, explainability highlights, and log history dashboard |
| `configs/training.yaml` | Hyperparameter configurations for email and URL models |
| `docs/PRD.md` | Product Requirements Document (Markdown) |
| `docs/PhishingDetection_PRD_RoBERTa.docx` | Compiled Product Requirements Document (Word format) |
| `src/preprocess/clean_and_map.py` | Standalone script for cleaning, mapping labels, and balancing datasets |
| `src/preprocess/dataset_builder.py` | Creates stratified train/validation/test splits |
| `src/preprocess/download_hf_dataset.py` | Programmatic downloader for Hugging Face Hub datasets |
| `src/preprocess/email_parser.py` | Text extractor parsing HTML to plain text and regex URL finder |
| `src/preprocess/tokenize_datasets.py` | Tokenizes dataset splits and outputs PyTorch format datasets |
| `src/preprocess/url_normalizer.py` | Normalizes URL strings and strips tracking parameters |
| `src/preprocess/visualize_distribution.py` | Visualizes dataset distribution and split stats |
| `src/models/train_roberta.py` | Main script to load tokenized datasets and fine-tune RoBERTa-base |
| `src/models/evaluate_roberta.py` | Computes test-split evaluation metrics and confusion matrices |
| `src/models/evaluation_report.py` | Generates summary classification report text file |
| `src/models/generate_report.py` | Generates diagnostic plots and confusion matrix images |
| `src/pipeline/aggregator.py` | Implementation of security aggregation and fallback rules |
| `scripts/build_prd_docx.py` | Script to convert the PRD sections into Word format |
| `scripts/eda.py` | Script to compute class statistics, word counts, and top words |
| `scripts/test_api.py` | Quick API integration smoke-test script |
| `tests/` | Unit test suite covering backend API, aggregator, and preprocessing rules |
| `reports/` | Output directory containing generated confusion matrices and evaluation reports |
| `data/` | Data folder containing raw, processed, and tokenized splits (gitignored) |
| `models/` | Saved local model weights checkpoints directory (gitignored) |

## 12. Implementation Milestones

| Phase | Deliverables | Duration |
| --- | --- | --- |
| 1. Data collection | Raw datasets downloaded and documented | 1 week |
| 2. Preprocessing | Email parser, URL normalizer, train/val/test splits | 1 week |
| 3. Baseline sanity checks | Dataset stats and simple non-transformer reference metrics | 3 days |
| 4. RoBERTa email training | Fine-tuned `email-roberta` checkpoint and metrics | 1 week |
| 5. RoBERTa URL training | Fine-tuned `url-roberta` checkpoint and metrics | 1 week |
| 6. Backend API Development | FastAPI implementation, auth, and batch routes | 4 days |
| 7. Combined pipeline | Routing logic and end-to-end inference path | 4 days |
| 8. Streamlit Client | UI with authentication, batch submission, and metrics | 4 days |
| 9. Evaluation write-up | Final metrics, error analysis, README | 4 days |

## 13. Risks And Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Few high-quality phishing emails | High | Use class weights, careful augmentation, and external held-out evaluation |
| Model memorizes dataset artifacts | High | Deduplicate, evaluate across sources, inspect false positives and false negatives |
| GPU memory limitations | Medium | Use batch size 8, gradient accumulation, max length caps, and Docker CPU fallback |
| URL strings may lack semantic context | Medium | Preserve URL structure and optionally add engineered features later |
| Demo app may run before models exist | Low | App shows a clear missing-model warning |
| API vulnerable to large payloads | Medium | Enforce maximum payload limits (e.g., 5MB) via FastAPI middleware |
| API abuse and Denial-of-Service | High | Implement client IP-based rate limiting (100 requests per 60 seconds) via FastAPI middleware |

## 14. Release Criteria

- Docker build completes.
- Unit tests pass.
- FastAPI backend and Streamlit app communicate successfully.
- Authentication successfully secures the API endpoints.
- Training scripts accept processed CSV inputs.
- RoBERTa-only design is reflected in code, README, and documentation.
- Final report includes separate email, URL, and combined pipeline metrics.

## 15. Open Questions

All initial open questions have been resolved during implementation:
- **Model Checkpoints**: Checkpoints are stored locally in the `models/` directory. Direct integration with Hugging Face Hub can be enabled via environment tokens.
- **Training Environment**: The codebase is configured to run training either on local CUDA GPU or fall back to CPU.
- **Live Lookups**: The system features a static local allowlist (`KNOWN_SAFE_DOMAINS`) in the routing logic to bypass model inference for highly trusted domains. Active live lookup feeds are planned for future revisions.
- **Explainability**: Model explainability using Gradient Norm (Saliency) mapping is fully implemented, allowing users to see visual feedback of word importances directly in the Streamlit UI.
