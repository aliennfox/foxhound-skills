# FoxHound Skills

Fox 的 AI Agent Skills 集合，跨 agent 共享。

## 安装

### 一键全装（推荐）
```bash
npx skills add aliennfox/foxhound-skills --all -g -y
```

### 装到特定 agent
```bash
npx skills add aliennfox/foxhound-skills --all -a claude-code -g -y
npx skills add aliennfox/foxhound-skills --all -a openclaw -g -y
npx skills add aliennfox/foxhound-skills --all -a cursor -g -y
```

### 装特定 skill
```bash
npx skills add aliennfox/foxhound-skills --skill stock-analysis -g -y
```

### 手动 clone
```bash
git clone https://github.com/aliennfox/foxhound-skills.git
# 然后 symlink 到各 agent skills 目录
```

## 同步更新
```bash
npx skills update
# 或
cd foxhound-skills && git pull
```

## Skills 列表

见各子目录，每个包含 `SKILL.md`。
