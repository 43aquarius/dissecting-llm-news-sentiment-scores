# 交付物 8：投稿前检查清单（v6.2，2026-10-20）

对应执行提示词《当前论文的实质性改进与 SCI/SSCI 投稿准备》第八节交付物 8。
对象稿件：`download/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf`（v6.2，40 页，含封面）
复现包：`download/Replication_Package_v2_Audit.zip`
GitHub：`https://github.com/43aquarius/dissecting-llm-news-sentiment-scores`（Release v6.0.0 / v6.1.0 / v6.2.0 / v6.3.0 / v6.3.1）

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
- [x] Conflict-of-interest / funding 声明已补全（v6.3.1：WP titleblock 声明区 + declarations_FRL.md + cover letter 三处一致，标准无冲突/无资助语句；作者投稿前作事实性核对即可）

### 复现包与 GitHub
- [x] 复现包独立编译冒烟通过；包内测试网同 297 断言（v6.3.1）
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

## 四、投稿前剩余动作（按优先级；2026-10-23 第三轮更新：v6.3.1）

1. ~~**FRL 格式适配**~~ → **✅ 已完成（2026-10-20）**：官方指南实际要求 **<2,500 词**（非前轮假设的约 9,000 词，已修正）。已产出 **FRL letter 版** `submission_frl/frl_letter.pdf`（6 页，正文 1,408 词，2 表，18 引用）+ `frl_letter.tex` 源码 + `scripts/frl_letter_check.py`（**109/109 断言**：数字=存档、措辞守卫、词数上限）。40 页完整工作论文作 online appendix。定位修正与 letter 决策记录见 `Submission_Package_and_Positioning.md` 二·补节。
2. ~~**匿名版制备**~~ → **✅ 无需（已核验）**：FRL 为单盲评审（SciRev：审稿人可见作者名），单盲下不要求匿名稿；如后续改投双盲期刊再按此清单制备（复现包链接需匿名化处理，仓库名含作者 ID `43aquarius`）。
3. ~~**COI/funding 声明**~~ → **✅ 已填入（2026-10-23，v6.3.1）**：标准无冲突/无资助语句已按作者指令写入 `declarations_FRL.md` 第 1、2 节、`cover_letter_FRL.md` 与 WP titleblock 声明区三处。⚠️ 系约束性法律声明：**投稿利那一下须由作者事实性核对**（若作者有资助/冲突须改写）。
4. ~~**cover letter**~~ → **✅ 已完成并终稿化（v6.3.1）**：`submission_frl/cover_letter_FRL.md`（letter 定位、去识别/构成/随机性/等效性四亮点、单模型诚实声明、AI 披露；COI/funding 占位于 v6.3.1 落地为正式语句）。
5. ~~**highlights**~~ → **✅ 已完成**：`submission_frl/highlights.txt`（5 条，逐条 ≤85 字符，脚本核验）。
6. **作者可选实验**（不阻塞投稿）：人工双标注员 κ（annotation_package 即取即用）；3–5 供应商跨模型复现（设计与可证伪预测已存档于复现包）。

### ~~新增待修记录~~ → **✅ 已修（2026-10-23，v6.3.1）**
- ~~WP 附录 G "sessions 3–4 固定构成漂移 +0.57 (t=0.3)" 舍入笔误~~ → 正文两处已改 **+0.56**（appendix.tex/results.tex），`tests/test_numbers.py` 新增 7 条守卫（钉值 0.5645±0.0005、双文件 +0.56 渲染、+0.57 短语禁用、COI/funding 存在），测试网 290→**297 断言全过**，WP 重编译重合并，pdf_qa 65/65。详见 `P2_v6_revision_log.md` v6.3.1 节。
- **GitHub PAT 轮换**（安全，作者执行；**仍为唯一安全待办**）：fine-grained token 曾在聊天明文出现并用于多次推送与 Release 发布，建议立即在 GitHub → Settings → Developer settings → Fine-grained tokens 撤销并重建。
