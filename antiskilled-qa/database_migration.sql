-- ============================================
-- Antiskilled QA Evaluations Table
-- 质量评估结果存储
-- ============================================

-- 创建 qa_evaluations 表
CREATE TABLE IF NOT EXISTS qa_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    evaluator VARCHAR(100) NOT NULL,  -- 'anthropic/claude-sonnet-4', 'manual', etc.
    
    -- === 7 维度评分 (0-10) ===
    accuracy_score DECIMAL(3,1) NOT NULL,
    completeness_score DECIMAL(3,1) NOT NULL,
    readability_score DECIMAL(3,1) NOT NULL,
    signal_quality_score DECIMAL(3,1) NOT NULL,
    hype_assessment_score DECIMAL(3,1) NOT NULL,
    structural_quality_score DECIMAL(3,1) NOT NULL,
    claims_quality_score DECIMAL(3,1) NOT NULL,
    
    -- === 总分和等级 ===
    total_score DECIMAL(4,2) NOT NULL,
    grade VARCHAR(1) NOT NULL,  -- A/B/C/D/F
    
    -- === 详细反馈 (JSONB) ===
    issues JSONB DEFAULT '{}'::jsonb,  -- 每个维度的问题列表
    recommendations JSONB DEFAULT '[]'::jsonb,  -- 改进建议
    strengths JSONB DEFAULT '[]'::jsonb,  -- 优点
    
    -- === 元数据 ===
    evaluation_duration_seconds INTEGER,
    tokens_used INTEGER,
    
    -- === 审计 ===
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- === 约束 ===
    CONSTRAINT valid_scores CHECK (
        accuracy_score BETWEEN 0 AND 10 AND
        completeness_score BETWEEN 0 AND 10 AND
        readability_score BETWEEN 0 AND 10 AND
        signal_quality_score BETWEEN 0 AND 10 AND
        hype_assessment_score BETWEEN 0 AND 10 AND
        structural_quality_score BETWEEN 0 AND 10 AND
        claims_quality_score BETWEEN 0 AND 10 AND
        total_score BETWEEN 0 AND 10
    ),
    CONSTRAINT valid_grade CHECK (grade IN ('A', 'B', 'C', 'D', 'F'))
);

-- 索引
CREATE INDEX idx_qa_evaluations_video_id ON qa_evaluations(video_id);
CREATE INDEX idx_qa_evaluations_grade ON qa_evaluations(grade);
CREATE INDEX idx_qa_evaluations_total_score ON qa_evaluations(total_score);
CREATE INDEX idx_qa_evaluations_evaluated_at ON qa_evaluations(evaluated_at DESC);

-- GIN 索引用于 JSONB 查询
CREATE INDEX idx_qa_evaluations_issues ON qa_evaluations USING GIN (issues);

-- 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_qa_evaluations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER qa_evaluations_updated_at
    BEFORE UPDATE ON qa_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION update_qa_evaluations_updated_at();

-- ============================================
-- 查询视图 (方便聚合统计)
-- ============================================

CREATE OR REPLACE VIEW qa_evaluation_summary AS
SELECT
    DATE(evaluated_at) as evaluation_date,
    evaluator,
    COUNT(*) as total_evaluations,
    AVG(total_score) as avg_total_score,
    AVG(accuracy_score) as avg_accuracy,
    AVG(completeness_score) as avg_completeness,
    AVG(readability_score) as avg_readability,
    AVG(signal_quality_score) as avg_signal_quality,
    AVG(hype_assessment_score) as avg_hype_assessment,
    AVG(structural_quality_score) as avg_structural,
    AVG(claims_quality_score) as avg_claims,
    COUNT(CASE WHEN grade = 'A' THEN 1 END) as grade_a_count,
    COUNT(CASE WHEN grade = 'B' THEN 1 END) as grade_b_count,
    COUNT(CASE WHEN grade = 'C' THEN 1 END) as grade_c_count,
    COUNT(CASE WHEN grade = 'D' THEN 1 END) as grade_d_count,
    COUNT(CASE WHEN grade = 'F' THEN 1 END) as grade_f_count
FROM qa_evaluations
GROUP BY DATE(evaluated_at), evaluator
ORDER BY evaluation_date DESC, evaluator;

-- ============================================
-- 常用查询函数
-- ============================================

-- 获取最差的 N 个视频
CREATE OR REPLACE FUNCTION get_worst_qa_videos(limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    video_id UUID,
    total_score DECIMAL,
    grade VARCHAR,
    evaluated_at TIMESTAMPTZ,
    main_issues TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        q.video_id,
        q.total_score,
        q.grade,
        q.evaluated_at,
        ARRAY(
            SELECT jsonb_array_elements_text(
                q.issues->'accuracy' || 
                q.issues->'completeness' || 
                q.issues->'signal_quality'
            )
            LIMIT 5
        ) as main_issues
    FROM qa_evaluations q
    ORDER BY q.total_score ASC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- 获取需要重新处理的视频（低分）
CREATE OR REPLACE FUNCTION get_videos_needing_reprocess(min_score DECIMAL DEFAULT 5.0)
RETURNS TABLE (
    video_id UUID,
    video_title TEXT,
    total_score DECIMAL,
    grade VARCHAR,
    primary_issue TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        q.video_id,
        v.title as video_title,
        q.total_score,
        q.grade,
        (
            SELECT jsonb_array_elements_text(q.issues->'accuracy')
            LIMIT 1
        ) as primary_issue
    FROM qa_evaluations q
    JOIN videos v ON q.video_id = v.id
    WHERE q.total_score < min_score
    ORDER BY q.total_score ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 示例查询
-- ============================================

-- 查看最近 7 天的评估统计
COMMENT ON VIEW qa_evaluation_summary IS 
'Example: SELECT * FROM qa_evaluation_summary WHERE evaluation_date > NOW() - INTERVAL ''7 days'';';

-- 查找特定类型的问题
COMMENT ON TABLE qa_evaluations IS 
'Example: SELECT video_id, issues->>''accuracy'' FROM qa_evaluations WHERE issues->>''accuracy'' LIKE ''%price%'';';

-- 获取最差的 10 个视频
COMMENT ON FUNCTION get_worst_qa_videos IS 
'Example: SELECT * FROM get_worst_qa_videos(10);';

-- ============================================
-- RLS (Row Level Security) - 可选
-- ============================================

-- 启用 RLS（如果需要权限控制）
-- ALTER TABLE qa_evaluations ENABLE ROW LEVEL SECURITY;

-- 示例策略：只允许读取
-- CREATE POLICY "Allow read for authenticated users" ON qa_evaluations
--     FOR SELECT
--     USING (auth.role() = 'authenticated');

-- ============================================
-- 插入测试数据（可选）
-- ============================================

-- 示例：手动插入一条评估记录
-- INSERT INTO qa_evaluations (
--     video_id,
--     evaluator,
--     accuracy_score,
--     completeness_score,
--     readability_score,
--     signal_quality_score,
--     hype_assessment_score,
--     structural_quality_score,
--     claims_quality_score,
--     total_score,
--     grade,
--     issues,
--     recommendations,
--     strengths
-- ) VALUES (
--     'VIDEO_UUID_HERE',
--     'anthropic/claude-sonnet-4',
--     9.0, 8.5, 9.5, 8.0, 9.0, 9.0, 7.5,
--     8.64,
--     'B',
--     '{"accuracy": ["Price format inconsistency"], "completeness": ["Missing secondary ticker"]}'::jsonb,
--     '["Convert prices to Decimal type", "Add missing tickers"]'::jsonb,
--     '["Excellent financial metrics extraction", "Comprehensive risk discussion"]'::jsonb
-- );

-- ============================================
-- 结束
-- ============================================
COMMENT ON TABLE qa_evaluations IS 'Antiskilled AI 输出质量评估结果';
