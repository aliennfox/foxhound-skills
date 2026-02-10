#!/bin/bash
# ============================================
# Antiskilled 每日 QA 评估自动化脚本
# ============================================

set -e  # 遇到错误立即退出

# === 配置 ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANTISKILLED_DIR="/home/ubuntu/clawd/Antiskilled"
VIDEO_DIR="${ANTISKILLED_DIR}/temp"
QA_OUTPUT_DIR="${ANTISKILLED_DIR}/qa_reports"
MIN_SCORE=7.0
LOG_FILE="/tmp/antiskilled_qa_$(date +%Y%m%d).log"

# === 日志函数 ===
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ ERROR: $*" | tee -a "${LOG_FILE}" >&2
}

# === 检查环境 ===
if [ ! -f "${ANTISKILLED_DIR}/.env" ]; then
    log_error "Antiskilled .env 文件不存在"
    exit 1
fi

# 加载环境变量
set -a
source "${ANTISKILLED_DIR}/.env"
set +a

if [ -z "$OPENROUTER_API_KEY" ]; then
    log_error "OPENROUTER_API_KEY 未设置"
    exit 1
fi

# === 激活虚拟环境 ===
if [ -d "${ANTISKILLED_DIR}/.venv" ]; then
    source "${ANTISKILLED_DIR}/.venv/bin/activate"
    log "✅ 虚拟环境已激活"
else
    log_error "虚拟环境不存在: ${ANTISKILLED_DIR}/.venv"
    exit 1
fi

# === 创建输出目录 ===
mkdir -p "${QA_OUTPUT_DIR}"

# === 执行批量评估 ===
log "🔍 开始批量评估..."
log "  视频目录: ${VIDEO_DIR}"
log "  输出目录: ${QA_OUTPUT_DIR}"
log "  最低分数: ${MIN_SCORE}"

cd "${SCRIPT_DIR}"

python evaluate.py batch \
    --video-dir "${VIDEO_DIR}" \
    --output-dir "${QA_OUTPUT_DIR}" \
    --min-score "${MIN_SCORE}" \
    2>&1 | tee -a "${LOG_FILE}"

EVAL_EXIT_CODE=$?

if [ $EVAL_EXIT_CODE -ne 0 ]; then
    log_error "评估失败，退出码: ${EVAL_EXIT_CODE}"
    exit $EVAL_EXIT_CODE
fi

log "✅ 批量评估完成"

# === 生成报告 ===
log "📊 生成 CSV 报告..."

python generate_report.py \
    --qa-dir "${QA_OUTPUT_DIR}" \
    --output "${QA_OUTPUT_DIR}/summary_$(date +%Y%m%d).csv" \
    --stats \
    2>&1 | tee -a "${LOG_FILE}"

log "✅ 报告生成完成"

# === 保存到数据库 ===
log "💾 保存 QA 结果到数据库..."

python save_to_db.py batch \
    --qa-dir "${QA_OUTPUT_DIR}" \
    2>&1 | tee -a "${LOG_FILE}"

DB_EXIT_CODE=$?

if [ $DB_EXIT_CODE -ne 0 ]; then
    log_error "数据库保存失败，退出码: ${DB_EXIT_CODE}"
    # 不退出，继续生成告警
fi

# === 检查低分视频并告警 ===
LOW_SCORE_COUNT=$(find "${QA_OUTPUT_DIR}" -name "*_qa.json" -type f | wc -l)

if [ "$LOW_SCORE_COUNT" -gt 0 ]; then
    log "⚠️  发现 ${LOW_SCORE_COUNT} 个低分视频（<${MIN_SCORE}）"
    
    # 可选：发送 Telegram 通知
    if command -v openclaw &> /dev/null; then
        log "📱 发送 Telegram 通知..."
        openclaw message send \
            --channel telegram \
            --message "⚠️ Antiskilled QA Alert: ${LOW_SCORE_COUNT} 个视频低于 ${MIN_SCORE} 分" \
            2>&1 | tee -a "${LOG_FILE}" || log_error "Telegram 通知失败"
    fi
else
    log "✅ 所有视频质量达标"
fi

# === 清理旧文件（保留 30 天）===
log "🧹 清理 30 天前的旧 QA 报告..."
find "${QA_OUTPUT_DIR}" -name "*_qa.json" -mtime +30 -delete 2>&1 | tee -a "${LOG_FILE}"
find "${QA_OUTPUT_DIR}" -name "summary_*.csv" -mtime +30 -delete 2>&1 | tee -a "${LOG_FILE}"

log "✅ 每日 QA 评估完成"
log "📄 完整日志: ${LOG_FILE}"

exit 0
