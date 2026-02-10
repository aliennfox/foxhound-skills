# Changelog

All notable changes to the Antiskilled QA skill will be documented in this file.

## [1.0.0] - 2026-01-03

### Added
- **Complete evaluation framework** with 7 quality dimensions
- **Automated evaluation script** (`evaluate.py`) for single/batch processing
- **Report generation** (`generate_report.py`) with CSV/HTML output
- **Database integration** (`save_to_db.py`) for Supabase storage
- **Daily automation script** (`daily_qa.sh`) with cron support
- **Test example** (`test_example.py`) for quick validation
- **Comprehensive documentation**:
  - SKILL.md - Full evaluation framework
  - README.md - Quick start guide
  - INDEX.md - File navigation
  - EXAMPLE_OUTPUT.json - Sample QA result

### Evaluation Dimensions
1. **Accuracy (准确性)** - Data consistency with source (ticker, prices, timestamps)
2. **Completeness (完整性)** - Missing signals or key information
3. **Readability (可读性)** - Natural language without jargon overload
4. **Signal Quality (信号质量)** - Conviction, action, reasoning appropriateness
5. **Hype Assessment (Hype 评估)** - 6-dimension hype scoring accuracy
6. **Structural Quality (结构化质量)** - Summary sections, highlight tokens
7. **Claims Quality (Claims 质量)** - Verifiable assertions extraction accuracy

### Features
- Claude Sonnet 4 as evaluator (via OpenRouter)
- Flexible scoring system (0-10 per dimension)
- Grade system (A/B/C/D/F)
- Detailed issue tracking and recommendations
- Token usage and performance metrics
- Batch processing with filtering (--min-score)
- Database views and query functions
- HTML/CSV reporting with statistics

### Cost Optimization
- Only save low-score videos (<7.0 by default)
- Optional Claude Haiku support for cheaper evaluation
- Transcript truncation (8000 chars) to reduce tokens

### Integration
- Compatible with Antiskilled project structure
- Supabase schema included (`database_migration.sql`)
- OpenClaw automation support
- Telegram alerting for low-score videos

---

## Roadmap

### [1.1.0] - Planned
- [ ] Add human annotation interface for calibration
- [ ] Implement inter-rater reliability metrics
- [ ] Support for Chinese video evaluation
- [ ] Automatic prompt optimization based on QA results
- [ ] Real-time evaluation dashboard (web UI)

### [1.2.0] - Planned
- [ ] A/B testing framework for different LLM evaluators
- [ ] Historical trend analysis (quality over time)
- [ ] Custom scoring weight adjustment
- [ ] Integration with GitHub Actions for CI/CD

---

## Contributing
Contributions are welcome! Please open an issue or PR for bugs, improvements, or new features.

---

**Maintained by**: Claude (OpenClaw Agent)
