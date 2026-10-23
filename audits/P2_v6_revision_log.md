# P2 修订执行报告（v6 轮，2026-10-19）：三层方案落实情况

**对应论文**：*Dissecting LLM News Sentiment Scores: Identity Priors, Batch Composition, Scoring Noise, and Price Echoes in Return Predictability*（Chang Tan, Dalian University of Technology）

本报告对应您提出的三层修订方案，逐项说明实际执行情况。所有改动均有脚本/检索证据支撑，未核实的内容如实标注。

---

## 第一层：必须改的硬伤和投稿规范（全部完成 ✅）

| # | 您的要求 | 执行结果 |
|---|---------|---------|
| 1 | 人类作者 + AI 披露 | 作者改为 **Chang Tan**（Dalian University of Technology，aquars43@foxmail.com）；首页新增 *Generative-AI use* 披露段：GLM-4-Plus 既是被研究工具也是研究助理、作者设计并核验全部结果、AI 非作者（符合 Elsevier 政策） |
| 2 | 摘要 ≤200 词 | 从 ~213 词压至 **198 词**，保留问题、设计、稳健结果与结论；测试网断言 ≤200 |
| 3 | 清除修订日志式表述 | 全文改写为**分阶段研究设计叙述**（"first pass"→"staged, pre-specified re-fielding sessions"）；earlier draft / retract / revision note / problem list / v2 draft / v4 inference 等 8 类短语全部清除，并写入 183 项断言回归网（未来改动若引入这类措辞会直接测试失败） |
| 4 | 5.4 节 1/14 比值 | 已改：clean 系数（0.003）是**价格语言组系数（0.047）的 1/14**、约为 baseline（0.0149）的 **0.22**——您的判断经数值核验完全正确 |
| 5 | 16.3%/16.2% 统一 | 底层值为 39/240=16.25%；统一为 **"39 of the 240 (16.2%)"**，与自动生成表一致 |
| 6 | Table 6 重复行/公司数 | **证实为真实 bug 且比疑似更严重**：生成器 `rows[0::3]` 步长切片错误 → 渲染后仅 **20/36 家**、8 家重复（QCOM 同行重复）、列合计 307/222≠341/240，而"Verified"注释只查了数据未查渲染。已修复为连续分块 + 新增**渲染级断言**（36 家唯一、列和相符），断言纳入测试网 |
| 7 | 2,664/2,628 说明 | 已核验 2,628 = 2,664 − 36（2026-07-01 无前收盘价的首日 firm-day）并写入 §5.5 与功效表注 |
| 8 | 参考文献逐条核验 | 全部 19+4 条经出版方/arXiv 元数据检索核验；修正：**Lopez-Lira(2025) 实为三作者（+Tang+Zhu）**；L&T JFE 2026 补卷期（Vol. 184, Art. 104335, DOI）；Chen et al. 年份改 2024；Teles 精确作者（两作者）与题名；Kang 精确题名；**officioso2026 两轮检索不可核实 → 按诚信原则删除**，替换为可核实的 Kirtac & Germano (2024, FRL 62, 105227) |
| 9 | glm-4-plus 写入方法 | §4.2 明写模型与默认解码；附录 A 解释 "thinking disabled" 含义（请求级开关，关闭思维链生成，非温度/种子覆写） |
| 10 | 价格回声降级 | 摘要/引言/§5.4/讨论/结论全链改为 **directional**（差异 p=0.10、power 0.31），不再与四项稳健发现并列 |

## 第二层：识别与论证力度补充实验

| # | 您的要求 | 执行结果 |
|---|---------|---------|
| 1 | 身份互换对照 + Visa 修正 + 语法通顺化 + 强制验证 | **预注册后执行**（`audits/P2_preregistration_session5.md` 先行存档，含可证伪预测）：S5=种子错换（seed 20261019，36 家错排映射存档）、P5=[Company X] 中性前缀、A5'=修正 Visa 泄露（335/341 改写、**强制验证 0 残留标识符**）+句首大写确定性平滑；六条件批内轮转、84 次调用。**数据已完成 63/84**，后遇服务方持续 429 配额封锁（>1.5 小时），静默冷却多次未恢复——按诚信原则，结果数值在数据完整前不写入论文（见下方"待定项"） |
| 2 | temperature=0 对照 | 同上（T0a/T0b 两轮）；探测确认 API 接受 temperature 参数且两次小测试输出一致 |
| 3 | 批次构成→下游后果 | **完成**（新脚本 `batch_downstream.py`）：7 个具名来源 β 全在 [0.010,0.016]、所有构成/重分批斜率差异 p>0.93；截面排名 ρ 0.81–0.92 稳健；但 **"score≥+50" 阈值交易数 22→50 翻倍**（会话3）/27→43（会话4），日度均值位移 +4.0~4.6 点、**逐日变号翻转 16–24%**。已写入附录新表 + §5.2 + 讨论——这就是审稿人要的"危害是什么"的定量答案 |
| 4 | NLP 文献 + 收敛 never quantified + 批次机制 | 新增 BatchPrompt (ICLR 2024)、Lost in the Middle (TACL 2024)、Zheng et al. (ICLR 2024) 三条核验文献；§2.3 新增 NLP 上下文效应段；措辞收敛为 "not previously quantified **in the LLM-finance setting**" 并注明 NLP 已记录邻近现象但未量化其对数值测量工具水平的影响；机制推导的未闭合部分维持如实声明 |
| 5 | 人工标注（≥2 名独立标注员 + κ） | **环境内无法产生真人标注，不伪造**。已交付完整双标注员工具包（`annotation_package/`：52 条标注表+成文编码手册+独立标注协议+κ 计算脚本）；脚本在表未填时拒绝计算。论文附录如实声明"无人工金标准、包已备好"。**您本人可作为标注员 1**（填 rater1_label 列），再找一位同事填 rater2_label 列，运行 `kappa_analysis.py` 即得 κ 与一致性——这是拿到人工验证最快的方式 |
| 6 | 多模型验证 | **探测证实本环境不可行**：SDK 忽略 model 参数，所有请求均被路由至同一 glm-4-plus 端点（探测日志存档）。已如实写入限制与预注册不可行声明，不伪造跨模型结果。此实验需要具备多模型路由的真实 API 环境 |

## 第三层：结构与范围（完成 ✅）

- **主线收敛**：标题缩短为四通道（Identity Priors, Batch Composition, Scoring Noise, Price Echoes in Return Predictability），去掉 Coverage Selection 与 Short-Horizon
- **检验线下放**：期限路径、分位组合、异质性交互全部移入新附录 *Auxiliary Analyses*（§6 只留一句概括+指针）；删除"早期草稿存档结果"附录
- **辅助数值更新**：draw-stability 口径统一为 14 个具名 draw（含会话 4 双构成+随机重分批），β∈[0.0104, 0.0161]、t∈[1.47, 2.12]
- **投稿策略**：FRL 首投定位维持；cover letter 已按 v6 状态重写（新标题、人类作者、AI 披露段、下游后果亮点）；EL letter 版备选不变

---

## 会话 5 最终处置（本轮定案）

- 状态：数据 63/84 次调用完成（各条件 250–275/341）；服务方 429 封锁自 12:55 UTC 起持续 2 小时以上，含三次 ≥30 分钟完全静默冷却均未恢复（判定为硬性配额，非短窗限流）
- **按诚信原则定案为 Path A**：正文不报告会话 5 的任何估计值；摘要/结论/方法中的相关主张已相应收敛；附录改为《Pre-Registered Control Session (Archived Design)》，如实记载预注册文档、变换代码（含种子错排映射与零残留验证报告）、逐调用日志与部分数据的存档位置
- 恢复路径（无需任何设计变更）：配额恢复后依次运行 `llm_score_v5.mjs`（断点续跑，自动跳过已评分条目）→ `analysis_v5.py`（产出 results_s5.json）→ 将估计值按预注册分析计划写入论文 §5.2/§5.3 与附录，并重新通过 183+ 断言测试与编译 QA。预计需 ~10 分钟 API 时间

## 交付物状态

- 论文 v6（终版）：**35 页**（封面+34 页正文），Tectonic 0 error，pdf_qa_v6 37/37 关键串通过，页尺寸/字体/边距全过（仅封面页脚为设计元素）
- 回归测试：183/183 断言通过（表 6 渲染、16.2% 统一、2,628 算术、比值措辞、14-draw 区间、下游数值、修订日志短语禁用、摘要词数、文献存在性）
- 复现包 v2（v6 轮）：175 文件 / 10MB（src 58、data 52、audits 11、tests 1），manifest 55 行，README/notes 更新，标注包内置，包内论文独立编译冒烟通过（34 页）

## v6.2（2026-10-20）：完整执行提示词收尾轮——等效性检验与文献补全

**触发**：对照《当前论文的实质性改进与 SCI/SSCI 投稿准备》完整执行提示词逐项核查 v6.1，发现两个未落地项：(1) 第二阶段任务 B 核心的正式等效性检验（TOST）从未执行——全文存在"statistically indistinguishable"类措辞四处 + H4"indistinguishable from zero"一处，均为"未拒绝=相同"谬误实例；(2) 第四阶段点名的 Hansen/Bisharat/Kong/Licht 四条文献线索未核验。

**TOST 执行（新脚本 equivalence_testing.py，seed 20261020，B=9,999，与 analysis_v2/v3/v5 同构的日聚类 bootstrap，13 项重建点估计断言全过）**：
- 主界限 δ*=0.0074（基准具名系数 0.014892 的一半，"数量级相同"惯例；= 27 bps/1SD 冲击）；同时报告各对比的 EMT（等效界限阈值，margin-free）
- **升级**：四个去识别对比（跨会话/同会话/交错/会话5修正）全部在 δ* 下正式等效（EMT 0.0032–0.0062，即基准的 21–42%；功效 0.74–0.99）——"不变性"从"未发现差异"升级为"等效性发现"
- **限制**：换名对比边缘未过（EMT 0.0083=56%）；LM 词典对比双向不可判（EMT=4.4×基准、功效 0、80% 功效需 165×样本）——此前对词典马赛的任何"无差异"印象正式撤回为"不可判"；priced-clean 同样无等效可言（EMT=6.6×；其 90% 区间全正=单侧 5% 与双侧 p=0.100 同一事实）
- **H4 措辞修正**：clean 系数不能宣称"与零无异"（EMT 0.0136=91% 基准，需 6 倍样本）——"无 clean 信号"与"clean 信号近半基准"在本样本下同样不可分
- 探索性标注：修订阶段设计、族外报告、界限规则先于判定固定（theory §3.5 推断纪律的新增反向条款：非拒绝≠等效）

**论文改动**（正文 9 处 + 附录新小节）：
- theory 推断标准新增"非拒绝≠等效"原则句；results §5.1 预测层段落重写（TOST 判定段）；fig:forest 图注、§5.2 尾句、§5.4 H4 段、§6 两层结论、intro 第二发现段、discussion 综合 (ii)、litreview H2 括注全部改写为等效性感知措辞；摘要"without changing predictive content"→"formally equivalent"（≤200 词约束保持）
- 附错并改：litreview H2 括注残留的 v5 时代"a genuine negative prior"陈旧表述（与 v6.1 去识别结论矛盾）清除；robustness/附录波动率交互的"indistinguishable from zero"统一改为"no detectable difference"（避免与自设规则字面冲突）
- 新附录小节 app:equiv + tab:tost（8 对比 × EMT/功效/判定）；文献新增 4 条全核验引用

**文献核验轮**：Christensen & Hansen (AEA P&P 2026, DOI 10.1257/pandp.20261020) ✓、Bisharat & Hean (SSRN 7177498, 预印本如实标注) ✓、Kong et al. (arXiv:2602.14233, 十作者立场论文) ✓、Jo-Kim-Hee (arXiv:2610.22187, 量表敏感性——检索中的意外收获) ✓；**Licht 线索四轮检索不可核实→按诚信原则不引用**（详见 B 报告 B5 节）

**验收**：Tectonic 0 error 0 overfull（39 页正文）；tests/test_numbers.py 237→**290 断言全过**（+53：TOST 数值/判定一致性/新措辞守卫/新引用存在性/3 条新禁用短语）；合并封面 40 页；pdf_qa 65/65 关键串、0 字体、0 页面问题（仅封面页脚设计元素）

## v6.3.1（2026-10-23）：投稿就绪收尾轮——舍入笔误修正 + 声明补全

**触发**：用户指令"做成可以直接最终提交的产物"。对照 v6.3 检查清单，距直接投稿剩余三项：(1) v6.3 轮发现的 WP 附录 G/正文 +0.57 舍入笔误（存档值 0.5645 正确舍入应为 +0.56）仍在两处；(2) COI/funding 声明缺位（FRL 要求 Declaration of Interest）；(3) 相应的测试守卫与重打包。

**改动**：
- **舍入修正**：appendix.tex（"at fixed composition is $+0.56$"）与 results.tex（"at fixed composition measuring $+0.56$"）两处 +0.57→+0.56，与存档 results_s4.json 的 0.564516 一致；letter 侧无此问题（v6.3 制作时已采用 +0.56）
- **WP 声明补全**：titleblock.tex 声明区新增 "Competing interests and funding" 一句（无利益冲突 + 无专项资金资助），与 FRL declarations 文件口径一致；系作者指令下按标准默认语句填入，投稿前作者须事实性核对
- **投稿文件填充**：declarations_FRL.md 第 1/2 节由占位改为正式语句；cover_letter_FRL.md 的 [AUTHOR TO CONFIRM] 同步落地；两文件第 9 节"剩余动作"相应更新（第 1 项改为"事实性核对"）
- **测试网扩充**：test_numbers.py 290→**297 断言**（+7：s4 漂移钉值 0.5645±0.0005、+0.56 双文件渲染守卫、+0.57 两短语禁用守卫、COI/funding 声明存在守卫）

**工程坑记录**：tectonic 首轮编译被宏包缓存重下载超时静默打断（EXIT 经管道误报为 0，PDF 时间戳未变即识别）；重跑真实完成（"Writing main.pdf"）。

**验收**：Tectonic 0 error（39 页正文）；297/297 断言（项目级）；合并封面 40 页；pdf_qa_v6 65/65 关键串、0 字体问题、0 页尺寸问题（仅封面页脚设计元素在边距外，属封面设计）；pdftotext 独立复核：+0.56×2、+0.57×0、COI/funding 两句均渲染；letter 检查网 109/109（letter 无受影响内容，无需重编译）。
