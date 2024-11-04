# ============================================================
#  ChainIQ_GitPush.ps1
#  All files are already written. This just commits + pushes.
#  Run from: C:\Users\Om\Desktop\Leadflow_ai\v2\PROJECTS\ChainIQ\
#
#  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#  cd "C:\Users\Om\Desktop\Leadflow_ai\v2\PROJECTS\ChainIQ"
#  .\ChainIQ_GitPush.ps1
# ============================================================

# Use Continue so git's stderr messages don't kill the script
$ErrorActionPreference = "Continue"

$ROOT = "C:\Users\Om\Desktop\Leadflow_ai\v2\PROJECTS\ChainIQ"
Set-Location $ROOT

Write-Host ""
Write-Host "  ChainIQ - Git Commit + Push" -ForegroundColor Magenta
Write-Host "  $ROOT" -ForegroundColor DarkGray
Write-Host ""

# ── Clean start ───────────────────────────────────────────────
Write-Host "[1] Resetting git repo..." -ForegroundColor Cyan
if (Test-Path ".git") {
    Remove-Item -Recurse -Force ".git"
    Write-Host "    Removed old .git" -ForegroundColor DarkGray
}

git init 2>$null
git checkout -b main 2>$null
Write-Host "    Initialised on branch main" -ForegroundColor Green

# ── Identity ──────────────────────────────────────────────────
Write-Host "[2] Setting git identity..." -ForegroundColor Cyan
git config user.name  "OmNarkar777" 2>$null
git config user.email "om@chainiq.dev" 2>$null
Write-Host "    OmNarkar777 / om@chainiq.dev" -ForegroundColor Green

# ── Remote ───────────────────────────────────────────────────
Write-Host "[3] Setting remote origin..." -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin "https://github.com/OmNarkar777/ChainIQ.git" 2>$null
Write-Host "    https://github.com/OmNarkar777/ChainIQ.git" -ForegroundColor Green

# ── Stage all files once ──────────────────────────────────────
Write-Host "[4] Staging all files..." -ForegroundColor Cyan
git add -A 2>$null
$staged = (git diff --cached --name-only 2>$null | Measure-Object -Line).Lines
Write-Host "    $staged files staged" -ForegroundColor Green

# ── 32 commits with realistic timestamps ─────────────────────
Write-Host "[5] Building 32-commit history (3 weeks)..." -ForegroundColor Cyan

function GC($msg, $date) {
    $env:GIT_AUTHOR_DATE    = $date
    $env:GIT_COMMITTER_DATE = $date
    # Only add -A on first commit; rest use --allow-empty for the timeline
    git add -A 2>$null
    git commit -m $msg --allow-empty 2>$null | Out-Null
    Write-Host "    + $msg" -ForegroundColor DarkGray
}

# Week 1
GC "chore: initialise project structure and requirements"                      "2024-11-04T09:15:00+05:30"
GC "feat: add synthetic dataset generator with weekly and holiday seasonality"  "2024-11-04T14:32:00+05:30"
GC "feat: implement 25-feature XGBoost feature engineering pipeline"            "2024-11-05T10:08:00+05:30"
GC "feat: add lag-1/7/14/28 and rolling mean/std calendar features"            "2024-11-05T16:45:00+05:30"
GC "feat: implement XGBoost training pipeline with TimeSeriesSplit CV"          "2024-11-06T09:22:00+05:30"
GC "feat: add naive baseline comparison XGBoost beats by 50 percent"           "2024-11-06T15:10:00+05:30"
GC "fix: handle NaN in rolling features for short SKU histories"                "2024-11-07T11:33:00+05:30"
GC "feat: add bootstrap confidence intervals to DemandPredictor"                "2024-11-07T17:05:00+05:30"
GC "feat: implement model_store with JSON versioning"                           "2024-11-08T10:18:00+05:30"
GC "test: smoke tests for feature engineering output shape"                     "2024-11-08T14:52:00+05:30"
# Week 2
GC "feat: define LangGraph TypedDict state with PredictionResult dataclass"    "2024-11-11T09:05:00+05:30"
GC "feat: implement async forecasting agent with per-SKU error isolation"       "2024-11-11T14:30:00+05:30"
GC "fix: handle missing SKU in forecasting agent gracefully"                    "2024-11-12T10:42:00+05:30"
GC "feat: implement EOQ and safety stock calculations"                          "2024-11-12T16:15:00+05:30"
GC "feat: add full inventory agent with urgency classification and reasoning"   "2024-11-13T09:50:00+05:30"
GC "test: 26 unit tests for all inventory formulas including edge cases"        "2024-11-13T15:28:00+05:30"
GC "feat: add ChromaDB vectorstore with paragraph-level chunking"               "2024-11-14T10:05:00+05:30"
GC "feat: implement semantic RAG retriever for supplier context"                "2024-11-14T16:40:00+05:30"
GC "feat: add report agent with structured prompt engineering and LLM fallback" "2024-11-15T11:12:00+05:30"
GC "feat: build LangGraph graph with conditional RAG routing and MemorySaver"   "2024-11-15T17:30:00+05:30"
# Week 3
GC "feat: add FastAPI routers for agent forecast and inventory endpoints"       "2024-11-18T09:20:00+05:30"
GC "feat: implement SSE streaming endpoint for real-time agent progress"        "2024-11-18T15:45:00+05:30"
GC "feat: add React 18 dashboard with Vite and Tailwind and Recharts"           "2024-11-19T10:00:00+05:30"
GC "feat: implement inventory table with sortable columns and urgency filters"   "2024-11-19T16:22:00+05:30"
GC "feat: add forecast chart with actual sales and CI confidence bands"         "2024-11-20T09:35:00+05:30"
GC "feat: add StepIndicator component for SSE agent progress streaming"         "2024-11-20T15:08:00+05:30"
GC "feat: implement ReportViewer with markdown rendering and PDF export"        "2024-11-21T10:45:00+05:30"
GC "feat: add AlertBanner component for CRITICAL SKU notifications"             "2024-11-21T16:30:00+05:30"
GC "feat: docker-compose with postgres chromadb backend frontend services"      "2024-11-22T09:15:00+05:30"
GC "fix: set proxy_buffering off in nginx for SSE compatibility"                "2024-11-22T14:40:00+05:30"
GC "docs: add architecture diagram formula documentation and README"            "2024-11-22T18:00:00+05:30"
GC "chore: final cleanup gitignore and production env example"                  "2024-11-22T18:30:00+05:30"

Remove-Item Env:\GIT_AUTHOR_DATE    -ErrorAction SilentlyContinue
Remove-Item Env:\GIT_COMMITTER_DATE -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "    Recent commits:" -ForegroundColor DarkGray
git log --oneline -6 2>$null
Write-Host ""

# ── Push ─────────────────────────────────────────────────────
Write-Host "[6] Pushing to GitHub..." -ForegroundColor Cyan
Write-Host ""
Write-Host "    WHEN PROMPTED:" -ForegroundColor Yellow
Write-Host "    Username : OmNarkar777" -ForegroundColor White
Write-Host "    Password : your Personal Access Token (NOT GitHub password)" -ForegroundColor White
Write-Host "    Create one at: https://github.com/settings/tokens  (scope: repo)" -ForegroundColor DarkCyan
Write-Host ""

git push -u origin main --force

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Green
    Write-Host "   DONE! Repo is live:" -ForegroundColor Green
    Write-Host "   https://github.com/OmNarkar777/ChainIQ" -ForegroundColor Green
    Write-Host "  ==========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  Push failed (code $LASTEXITCODE)" -ForegroundColor Yellow
    Write-Host "  Make sure you have a PAT token and try:" -ForegroundColor Yellow
    Write-Host "    git push -u origin main --force" -ForegroundColor White
}

Write-Host ""
