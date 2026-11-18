# AI Document Automation

Python tools that turn structured content into professional, print-ready PDFs: an **ATS-friendly resume generator** and a **consulting-style proposal generator**. Both were built through AI-assisted development with Claude (Anthropic): I set the requirements, reviewed every output and iterated on the design, and the AI helped write and refine the code.

## Why I built this

Writing resumes and proposals in Word takes hours of formatting, and every change risks breaking the layout. Here the content lives in one place (a JSON file or Python data) and the layout is code, so a new version takes seconds and always looks consistent.

## Projects

### 1. Resume generator (`resume-generator/`)

- Builds an **ATS version** (single column, no photo, no tables, standard headings) for online applications.
- Optionally builds a **designed version with a photo** for printing or emailing.
- All content comes from one JSON file, so one edit updates both versions.

```bash
cd resume-generator
pip install -r ../requirements.txt
python build_resume.py sample_resume.json                 # ATS version
python build_resume.py sample_resume.json --photo me.jpg  # + designed version
```

Sample output: [`resume-generator/output/`](resume-generator/output/)

### 2. Proposal generator (`proposal-generator/`)

Builds a 12-page, consulting-style proposal (portrait A4) for a 6-month operations and business development plan, including:

- Executive summary and current project landscape, backed by cited public sources
- Weighted feasibility scorecard and a value-versus-ease prioritisation matrix
- Illustrative revenue scenarios (low, base, high) with every assumption listed
- Six-month roadmap (Gantt) and quick wins
- Risk heat map (likelihood × impact), risk register and Plan B for every risk

Charts and diagrams are drawn as inline SVG/HTML and printed to PDF with headless Chromium.

```bash
cd proposal-generator
pip install -r ../requirements.txt
playwright install chromium
python build_proposal.py
```

Sample output: [`proposal-generator/output/`](proposal-generator/output/)

## Tools

Python · ReportLab · Playwright (headless Chromium) · HTML/CSS/SVG · Claude (AI-assisted development)

## What I learned

- Writing clear requirements and reviewing AI-generated code critically
- Designing documents that pass applicant tracking systems (ATS)
- Turning research into consulting-style exhibits: scorecards, matrices, heat maps and roadmaps

## Author

Ahmad Muazamil bin Ishak · [github.com/zamilisaac](https://github.com/zamilisaac)
