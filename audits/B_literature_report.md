# 交付物 B：文献与创新性审查报告

**检索工具**：z-ai web-search + page_reader（arXiv/SSRN/RePEc/ScienceDirect/出版社页），检索日期 2026-10-16。
**核实原则**：每条文献均有可访问来源链接；未经核实的细节不写入。

## B1. 核心文献对比矩阵（直接相关）

| 文献（核实状态） | 研究问题 | 数据/样本 | 方法 | 核心结论 | 与本稿差异 |
|---|---|---|---|---|---|
| **Lopez-Lira & Tang (2026), JFE 正式版**（ScienceDirect S0304405X26001066；SSRN 4412788，被引 ~8,900）✓ | ChatGPT 新闻情绪是否预测次日收益 | 美股 2021-2022，RavenPack 新闻标题 | GPT 打分（具名）+ 马赛 vs 词典/情感模型 | 次日预测显著；多空策略盈利；小公司效应更强 | 本稿为其"近期窗口 + GLM 模型"复现，样本小 2 个数量级；L&T 用商业新闻档案（时间戳精确），本稿用 web-search |
| **Glasserman & Lin (2023), arXiv:2309.17322**（被引 ~146）✓ | LLM 新闻情绪策略的前视偏差与干扰效应 | 美股新闻标题（训练窗口内 in-sample） | 原始 vs **匿名化**标题对照交易实验 | 样本内：匿名化策略表现更好→**干扰效应 > 前视偏差**；大公司更强 | 本稿无任何匿名化对照；G-L 为 in-sample 设计，**post-cutoff 匿名化对照仍是空白** |
| **Lopez-Lira et al. (2025), arXiv:2504.14765**（被引 ~109）✓ | LLM 经济预测的记忆化问题 | 宏观+金融数据，跨模型 | 知识截止前后召回测试 | LLM 记忆了训练期内数值；指令与掩码均无法阻止；**post-cutoff 无召回** | 本稿窗口（2026-07~10）大概率为 post-cutoff，但未做验证；本稿的"天然 OOS"声明需要此文献支撑+实证 |
| **Didisheim, Fraschini & Somoza (2025), Economics Letters 256:112602**（被引 ~21）✓ | LLM 金融分析中的可预测记忆 | 指数与个股层面 | 让 LLM"预测"已实现收益的召回测试 | **指数层面记忆显著大于个股层面**（LLM 记得指数走势，不记得个股） | 本稿为个股面板——按 D-F-S 结论个股层面记忆较弱，但未检验 |
| **Chen et al. (2025), AEA 2026 program** ✓ | LLM 如何解读历史收益/图表 | LLM 对收益序列的预测实验 | 提示式预测 | LLM 预测**过度外推近期表现**（动量式），存在正偏差 | **直接对应本稿审计发现的价格回声问题**：情绪分数含已实现价格信息时会机械性外推 |
| **Herrera-Poyatos et al. (2025), Frontiers in AI / arXiv:2504.04462**（被引 ~112）✓ | LLM 情绪分析的模型变异问题 (MVP) | 多模型多数据集情绪分类 | 系统性模型间比较 | 模型规模/标签偏差/架构导致情绪输出**显著不稳定** | 本稿单一模型单次评分，无重复调用/跨模型稳定性检验 |
| **LoGrasso & Richiardi (2025), mf-journal**（被引 ~5）✓ | ChatGPT 组合能否获得异常收益 | 新闻公告组合 | 回测 | 30 天内可获异常收益，**样本外表现差** | 佐证本稿对可交易性主张的弱化必要性 |
| **Kang et al. (2025), MDPI Electronics 14(6):1090**（被引 ~36）✓ | GPT-4o vs FinBERT 情绪分类 | 行业新闻 | 提示工程优化的分类比较 | GPT-4o 优于 FinBERT 至多 10%（分行业） | 本稿未与 FinBERT 类模型对比（数据不可行，见 C） |

## B2. 方法学与背景文献（部分列举，均已核实存在）

- Glasserman & Lin 同主题延伸："A Test of Lookahead Bias in LLM Forecasts"（arXiv:2512.23847, 2025-12）✓；"HindsightBench"（arXiv:2607.18867, 2026-07）✓ —— 前视偏差审计正在工具化。
- "Financial Language Models as Applied AI"（arXiv:2609.23703, 2026-09）✓：明确将 2024-06 之后视为 contamination-safe OOS 窗口——**与本稿窗口选择逻辑一致**。
- Officioso et al. (2026), zero-shot LLM 情绪+股价框架（ScienceDirect S0020025526006420）✓；Teles et al. (2025) arXiv:2510.15929（多 LLM 金融情绪比较）✓；Golabzaei et al. (2026) Sci Rep（FinGPT）✓。
- 原稿引用的经典文献（Tetlock 2007、Garcia 2013、Chan 2003、Da et al. 2011、Loughran-McDonald 2011/2016、Hong-Stein 1999 等）抽查全部真实 ✓。

## B3. 原稿创新性反向审查

| 原稿声称的贡献 | 审查结论 |
|---|---|
| "LLM 情绪预测次日收益" | **已被 L&T (2026 JFE) 直接覆盖**。本稿仅为小样本近期窗口复现，不构成独立贡献 |
| "LLM 优于 LM 词典（马赛）" | **已被 L&T 覆盖**；且原稿比较存在推断谬误（无差异检验）；Kang et al. 2025 等已做 LLM vs FinBERT，覆盖面更广 |
| "两日反转是新颖发现" | **部分新颖但不可靠**：p=0.042 边缘 + 多重检验 + 机械反转竞争解释未排除；Chan (2003) 已记录新闻后漂移-反转结构，并非无人涉及 |
| "大公司效应（与 L&T 相反）" | 推断谬误（无组间检验）+ 覆盖与市值机械相关（web-search 偏向大公司）——更可能是**选择偏差的产物**而非经济发现 |
| "AI 辅助科研工作流展示" | 不构成期刊贡献；worklog 型内容 |
| （未声称但实际存在）web-search 新闻的选择偏差量化 | **尚无文献系统量化**（检索未见） |
| （未声称）post-cutoff 身份/干扰效应 | **G-L (2023) 只做了 in-sample；post-cutoff 重复该对照 = 真实增量** |
| （未声称）标题价格回声污染量化 | **未见文献**（Chen et al. 2025 提供动机但不做新闻面板分解） |

## B4. 真实研究空白与定位结论

**空白 1（最重要）**：知识截止后的"公司身份效应"审计。G-L 在样本内发现干扰效应 > 前视偏差；Lopez-Lira (2025) 证明 post-cutoff 无召回。那么 post-cutoff 新闻上，具名 vs 匿名化评分的差异还存在吗？若存在 → 是"词典式公司先验"而非记忆；若不存在 → 支持 OOS 可信性。**该检验未被任何已检索文献完成**。

**空白 2**：LLM 情绪信号的"价格回声"分解。新闻标题（尤其搜索引擎采集的回顾性文章）内嵌已实现价格信息 → 情绪-收益相关部分是文本回声而非预测。Chen et al. (2025) 的外推发现提供机制解释，但无人做新闻面板分解。

**空白 3**：小样本 LLM 金融研究的推断可靠性。wild cluster bootstrap、系数差异检验、多重检验族在 LLM-金融文献中普遍缺失（L&T 亦未报告差异检验）。

**结论**：原稿按"复现+机制发现"定位不可辩护；按"**测量有效性审计**"定位有真实增量，且与本环境可执行的实验完全匹配。

## B5. 2026-10-20 补充核验轮（执行提示词第四阶段点名线索）

执行提示词点名八条文献线索。此前已核验：Lopez-Lira & Tang（JFE 2026 正式版）、Glasserman-Lin（arXiv WP）、Didisheim-Fraschini-Somoza（EL 2025）、批量提示/上下文效应 NLP 文献（BatchPrompt、Lost in the Middle、Zheng ICLR 2024）。本轮对剩余四条逐一检索核验（web 检索 + 逐条元数据确认）：

| 线索 | 核验结果 | 状态 | 处理 |
|---|---|---|---|
| "Hansen 2026 LLM 测量验证" | **已核实**：Christensen, T. & Hansen, S. (2026), "Performing Valid Inference with AI/ML-Generated Covariates: A Guide for Empirical Practice", *AEA Papers and Proceedings* 116, 92–97, DOI 10.1257/pandp.20261020（同行评审正式发表；AI 生成协变量的测量误差推断修正 + ValidMLInference 包；FOMC 情绪应用） | 同行评审 ✓ | 已引用（litreview 审计段落；连接 Remark 1 衰减框架） |
| "Bisharat & Hean AI 时代金融情绪评估" | **已核实**：Bisharat, A. (Loyola University Chicago) & Hean, O. (Dakota State University) (2026), "Evaluating Financial Sentiment in the Age of AI", SSRN preprint 7177498（十二种情绪模型：词典/金融 transformer/开源 LLM 的超越收益相关的评估） | SSRN 预印本（未经同行评审），按预印本状态如实标注 | 已引用（litreview 审计段落） |
| "Kong et al. 2026 金融 LLM 评估偏差" | **已核实**：Kong, Y., Lee, H., Hwang, Y., Lopez-Lira, A., Levy, B., Mehta, D., Wen, Q., Choi, C., Lee, Y., Zohren, S. (2026), "Evaluating LLMs in Finance Requires Explicit Bias Consideration", arXiv:2602.14233（2026-02-15 提交；立场论文：五大偏差 look-ahead/survivorship/narrative/objective/cost，164 篇 2023-25 论文综述中单一偏差讨论率 ≤28%，提出结构有效性框架+评估清单；第一作者与已引用的 nie2024survey 综述共享作者） | arXiv 预印本（立场论文），如实标注 | 已引用（litreview 审计段落；本文 H4/H5 即其 look-ahead/selection 条目的 within-study 实例） |
| "Licht et al. LLM 连续测量" | **四轮定向检索无法核实**到可引用的条目（检索词：Licht + LLM/continuous measurement/scoring/finance/arXiv 2025-2026）。检索中发现的相邻主题论文 arXiv:2610.22187 作者为 Jo/Kim/Hee，非 Licht | **不可核实** | **按诚信原则不引用**；以已核实的 Jo et al. (2026)（评分尺度敏感性）替代该线索的学术功能 |
| （检索中额外发现） | **已核实**：Jo, W., Kim, G., & Hee, M. S. (2026), "Change the Number, Change the Answer: Assessing Rating Scale Sensitivity in LLM-Based Text Scoring", arXiv:2610.22187（2026-10-15；量表格式/范围/符号单元素改变使标准化分数位移约 0.10、约 20% 文本换类；rubric 提示不降低敏感性） | arXiv 预印本，如实标注 | 已引用（litreview NLP 段落；本文水平通道=其设计敏感性的金融实例） |

**对新颖性主张的影响（B4 更新）**：四条新文献进一步支持而非削弱本文定位。(1) Christensen-Hansen 提供了 AI 协变量推断的形式方法，但不含任何水平通道（去识别、批次构成）的测量——本文的批次构成效应量化仍是空白；(2) Kong et al. 的偏差清单是立场性呼吁，无 within-study 实测——本文正是该呼吁的一个完整实例（且提供了他们清单未包含的批次构成条目）；(3) Bisharat-Hean 评估工具性能但不审计评分的条件敏感性；(4) Jo et al. 展示量表设计敏感性但不在金融收益预测语境。**"多通道联合测量审计"的核心空白主张在 2026-10-20 检索后仍然成立**，且本文已按"not previously quantified in the LLM-finance setting"的收敛措辞引用 NLP 邻近现象。
