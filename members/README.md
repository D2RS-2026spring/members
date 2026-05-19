# D2RS-2026spring Members & Data Analysis

本项目用于 D2RS-2026spring 课程的学生成员管理和数据分析。

## 📚 项目简介

本项目包含两个数据分析案例：

1. **Issue #1 - 学生加入申请数据分析**：从 GitHub Issue 中收集学生信息（学号、姓名、感兴趣方向）
2. **Issue #2 - AI模型性能投票分析**：分析学生对不同 AI 模型的偏好排序

生成的网站：https://d2rs-2026spring.github.io/members/

## 🛠️ 技术栈

- **Quarto**：可复现计算文档框架
- **R**：数据分析和可视化
- **GitHub API**：数据来源
- **GitHub Pages**：网站托管
- **GitHub Actions**：自动化部署

## 📁 项目结构

```
members/
├── .github/
│   └── workflows/
│       └── update-data.yml     # 自动更新数据的 GitHub Action
├── _quarto.yaml               # Quarto 配置文件
├── index.qmd                  # 首页
├── issue1_students.qmd       # Issue #1 分析文档
├── issue1_students.csv        # Issue #1 数据（CSV）
├── issue2_voting.qmd          # Issue #2 分析文档
├── issue2_voting.csv          # Issue #2 数据（CSV）
├── issue1_comments.json       # Issue #1 原始评论数据
├── issue2_comments.json       # Issue #2 原始评论数据
└── README.md
```

## 🚀 本地部署

### 前置要求

1. **R** (>= 4.0)：https://www.r-project.org/
2. **Quarto**：https://quarto.org/docs/get-started/
3. **Git**：版本控制
4. **gh CLI**：GitHub 命令行工具

### 安装 R 包

```r
# 在 R 中运行以下命令安装所需包
install.packages(c("httr", "jsonlite", "dplyr", "stringr", "ggplot2", "tidyr", "showtext"))
```

### 克隆项目

```bash
# 克隆仓库
git clone https://github.com/D2RS-2026spring/members.git
cd members

# 切换到 main 分支
git checkout main
```

### 本地预览

```bash
# 使用 Quarto 本地预览
quarto preview

# 或渲染为静态网站
quarto render
```

网站将在 http://localhost:4200 预览。

## 🔄 数据更新流程

### 手动更新

```bash
# 1. 获取最新的 Issue 评论数据
gh api repos/D2RS-2026spring/members/issues/1/comments --paginate > issue1_comments.json
gh api repos/D2RS-2026spring/members/issues/2/comments --paginate > issue2_comments.json

# 2. 重新渲染 Quarto 文档
quarto render

# 3. 提交更改
git add .
git commit -m "Update data $(date +%Y-%m-%d)"
git push origin main
```

### 自动更新

项目配置了 GitHub Actions，每天凌晨 3:00 自动运行：

1. 从 GitHub API 获取最新数据
2. 重新渲染 Quarto 文档
3. 部署到 gh-pages 分支
4. 自动清理 7 天前的旧提交

手动触发：在 GitHub Actions 页面点击 "Run workflow"

## 📊 部署到 GitHub Pages

### 方式 1：自动部署（推荐）

将更改推送到 main 分支后，GitHub Actions 会自动：
1. 渲染网站
2. 推送到 gh-pages 分支
3. GitHub Pages 自动更新

### 方式 2：手动部署

```bash
# 1. 在 main 分支渲染网站
git checkout main
quarto render

# 2. 切换到 gh-pages 分支
git checkout gh-pages

# 3. 复制网站文件到根目录
cp -r _site/* .

# 4. 添加 .nojekyll 文件
touch .nojekyll

# 5. 提交并推送
git add .
git commit -m "Deploy $(date +%Y-%m-%d)"
git push origin gh-pages
```

### 配置 GitHub Pages

1. 进入仓库设置 → Pages
2. Source 选择 "Deploy from a branch"
3. Branch 选择 "gh-pages"，目录选择 "/ (root)"
4. 保存设置

## 🔧 数据验证规则

### Issue #1 学号验证

- 必须以 `2025` 开头（华农 2025 级学生）
- 共 13 位数字
- 不合法的学号会在报告中列出

### 数据获取说明

- 使用 GitHub API 获取 Issue 评论
- 评论数据缓存到本地 JSON 文件
- 避免 API 限流：使用 gh CLI 或添加认证

## 📝 编写自定义分析

### 添加新的分析文档

1. 创建 `.qmd` 文件：

```markdown
---
title: "我的分析"
---

```{r}
# R 代码
summary(mtcars)
```
```

2. 更新 `_quarto.yaml` 添加导航链接：

```yaml
website:
  navbar:
    left:
      - href: my-analysis.qmd
        text: 我的分析
```

3. 重新渲染：

```bash
quarto render
```

## 🐛 常见问题

### Q: 渲染失败怎么办？

A: 检查 R 包是否已安装，查看错误信息进行调试。

### Q: API 限流怎么办？

A: 使用 gh CLI 认证后请求，或等待限流重置。

### Q: 中文显示异常？

A: 确保加载 showtext 包并配置中文字体：

```r
library(showtext)
font_add("WenQuanYi", "/System/Library/Fonts/wqy-microhei.ttc")
showtext_auto()
```

## 📄 许可证

MIT License

## 🙏 致谢

- Quarto: https://quarto.org/
- GitHub Pages: https://pages.github.com/
- RStudio: https://www.rstudio.com/
