# 交付物 8：投稿前检查清单（v6.2，2026-10-20）

对应执行提示词《当前论文的实质性改进与 SCI/SSCI 投稿准备》第八节交付物 8。
对象稿件：`download/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf`（v6.2，40 页，含封面）
复现包：`download/Replication_Package_v2_Audit.zip`
GitHub：`https://github.com/43aquarius/dissecting-llm-news-sentiment-scores`（Release v6.0.0 / v6.1.0 / v6.2.0）

---

## 一、八个交付物 → 文件映射（全部存在且为最终状态）

| # | 交付物 | 文件 | 状态 |
|---|---|---|---|
| 1 | 当前稿件审计报告（P0/P1/P2 分级） | `audit_reports/P0P1P2_problem_list.md`、`P0_data_code_audit.md` | ✅ P0 12 项全修（v4）、P1 5 项全修（v5/v5.1）、P2+七类方案全修（v6/v6.1）、等效性缺口本轮闭合（v6.2） |
| 2 | 数据与统计核验表 | `P0_data_code_audit.md`（13 项错误三态归类）+ `tests/test_numbers.py`（**290 断言**，论文数字=脚本输出，双层：数值 JSON + LaTeX 源码） | ✅ 290/290 |
| 3 | 理论框架修订方案 | 已执行于论文 §3：测量分解方程 eq:score（ι/η/ε/ρ/D 八成分）、Remark 1（A1/A2 可检验假设）、§3.5 推断标准（差异不推断+**非拒绝≠等效**新条款） | ✅ 执行完毕，方案即成稿 |
| 4 | 最低成本实验补强方案 | `C_research_plan.md`（方案）+ `P1_experiments_report.md`/`_addendum.md`（执行）：交错会话、机制轮、会话5 六条件、下游后果 | ✅ 已执行；剩余项见第四节 |
| 5 | 文献与新颖性分析 | `B_literature_report.md` B1–B5（B5 为 2026-10-20 核验轮） | ✅ 26 条引用全部核验 |
| 6 | 论文修改蓝图 | `P2_v6_revision_log.md`（三层方案+v6.1+v6.2 执行记录，逐节改动） | ✅ 蓝图已 100% 执行 |
| 7 | 目标期刊分析 | `Submission_Package_and_Positioning.md`（FRL 首选 / EL letter 备选 / JFE-JF-RFS 明确不投，分区信息含来源） | ✅ 定位维持 |
| 8 | 投稿前检查清单 | 本文档 | ✅ |

## 二、逐项就绪检查

### 数据与代码
- [x] 样本流转链可复算：542 → 341 窗口内 → 335 (rel≥30) → 276 firm-date → 240 firm-days（36 非交易日静默丢弃已在正文显式）→ 205 回归样本；H5 N=2,628=2,664−36
- [x] 全部评分会话（542 具名、341 匿名+3 重复、会话3 八轮+构成对照、会话4 反序、会话5 六条件 84 调用、探测指纹）原始 JSON+逐调用日志存档
- [x] 表 1/表 6 由 `descriptives.py`/`coverage_table.py` 脚本生成（渲染级断言防 E1/E2 类错误复发）
- [x] 随机种子全线记录（20261016/17/18/19/20），复现包 README 含依赖说明

### 统计与推断
- [x] BH 族（5 假设 7 对比）+ 族外对比分离标注；wild bootstrap（H1）、日聚类 bootstrap（差异）、双向聚类（回归）、批次聚类（水平对比）
- [x] 功效/MDE 全族报告（附录 E 表）+ **TOST 等效性评估**（附录 E 新小节，8 对比含 EMT margin-free 报告）
- [x] 措辞合规："未检测到差异"仅用于差异检验结论处；等效性主张仅在 TOST 支持处；词典对比声明"双向不可判"
- [x] 预注册链：会话3/4/5 设计文档先于数据存档；AsPredicted 表单+SHA-256 哈希绑定（时间线如实记录）

### 图表
- [x] 9 图（森林/分布/会话解剖/可靠性/回声/选择/异质性/下游/审计设计）全部脚本生成，图注数字动态计算
- [x] 表 8 张全部可溯源（tab:tost 为本轮新增）

### 文献
- [x] 26 条引用逐条核验（web 检索；正式发表/预印本状态如实区分；Licht 线索不可核实→不引用，B5 节记录）
- [x] 新颖性主张收敛措辞："not previously quantified in the LLM-finance setting"，无"首次/首个"高风险表述

### 披露与作者信息
- [x] 作者：Chang Tan（Dalian University of Technology，aquars43@foxmail.com）；PDF 元数据同步
- [x] Generative-AI use 声明（工具+研究助理双角色、作者全责、AI 非作者）
- [x] Data and code availability 声明
- [x] 无"AI 生成"类不适标识；封面为工作论文样式（WP-2026-10, Draft）
- [ ] ⚠️ **投稿前需补**：Conflict-of-interest / funding 声明（当前稿无；FRL 要求 Declaration of Interest）

### 复现包与 GitHub
- [x] 复现包独立编译冒烟通过；包内测试网同 290 断言
- [x] 敏感信息扫描零命中；双 Release 保留版本演进
- [ ] ⚠️ **GitHub PAT 已在聊天中明文出现，建议作者轮换令牌**（本轮用同一令牌推送 v6.2.0 后失效处理由作者决定）

## 三、结论强度终审（对照提示词第五节 10 条原则）

| 原则 | 状态 |
|---|---|
| 1 价格回声仅方向性（p=0.10，功效 0.31） | ✅ 全链一致；v6.2 补充"clean≠等效于零"的对称诚实 |
| 2 基准结果如实报告 BH/同日控制/抽样敏感性 | ✅ 摘要 t=2.10、q=0.062、t=1.82、draw-dependent [1.47,2.12] |
| 3 非拒绝≠等效 | ✅ **本轮新执行**：TOST 全对比+措辞清扫+理论条款 |
| 4 匿名化≠消除公司先验（去识别效应） | ✅ 换名对照否定公司先验；标题与全文一致 |
| 5 检测到选择≠校正选择 | ✅ H5 仅声明检测；无任何校正声明 |
| 6 不用有利场次掩盖不确定性 | ✅ 15 draws 全报告区间 |
| 7 预设/后设/探索三分离 | ✅ §3.5+附录逐项标注（TOST 标为探索性） |
| 8 结论↔表/检验/代码对应 | ✅ 290 断言回归网 |
| 9 未完成实验如实入局限 | ✅ 人工金标准/跨模型/精确时间戳三项如实声明 |
| 10 不选择性删除不利实验 | ✅ v1→v6.2 全部撤回与更正链写入论文与修订日志 |

## 四、投稿前剩余动作（按优先级）

1. **FRL 格式适配**（必须，作者执行）：正文压缩至期刊要求（FRL 研论文通常 ≤9,000 词左右，当前正文约 12,000 词）；参考文献转 FRL 样式；图表单列适配。建议路径：主体投 FRL；附录 A（最小可行审计协议）可发展为独立 practitioner 短文。
2. **匿名版制备**（投稿系统要求时）：titleblock 去作者信息+致谢；复现包链接改为匿名引用方式（GitHub 仓库名含作者 ID `43aquarius`，双盲评审需用匿名仓库或改为"available upon request"）。
3. **COI/funding 声明**（必须）：一句话即可（无资助、无利益冲突或如实声明）。
4. **cover letter**：`Submission_Package_and_Positioning.md` 已含 v6 版草稿，需按 v6.2 更新亮点（补：TOST 等效性框架、四条 2026 新文献、Kong et al. 清单呼应）。
5. **作者可选实验**（不阻塞投稿）：人工双标注员 κ（annotation_package 即取即用）；3–5 供应商跨模型复现（设计与可证伪预测已存档于复现包）。
