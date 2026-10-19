# 投稿定位、回应函状态与 Cover Letter

**日期**：2026-10-18
**对象**：v5.1 稿（33 页，download/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf）

---

## 一、投稿就绪度评估（五角色联合判断）

| 维度 | 状态 | 依据 |
|---|---|---|
| 数据与代码可复现 | ✅ 完备 | 133 项断言回归网；包内独立编译冒烟测试通过；全部数字可溯源到脚本输出 |
| 核心结论稳健性 | ✅ 已确证 | 身份先验（−2.82，轮级 t=6.8/聚类 t=2.7，4 轮全负）；构成效应（+3.56 合并 z=3.4，两会话反转顺序复现）；H1 如实降级为边际/抽样依赖 |
| 推断纪律 | ✅ 最高标准 | 调用聚类、BH 家族、差异检验而非分别显著性、功效披露、家族外对照如实标注 |
| 原创性 | ✅ 明确 | 五通道联合测量 + 批次构成效应（文献未量化）+ 非对称锚定 + 响应级情绪分解 + 伸缩恒等式反直觉论证 |
| 主要弱点 | ⚠️ 如实声明 | 单模型/单端点；205 观察功效有限；无人工金标准；LLM 辅助分类非独立标注；机制定量推导未闭合 |

**判断**：论文达到可投稿状态。剩余弱点全部在限制章节如实声明，不构成诚信风险；单模型与功效弱点是 FRL/EL 层级可接受的（该层级论文普遍如此），机制未闭合部分已转化为"开放问题+可复制目标"的贡献表述。

## 二、期刊定位（基于核验信息）

**首选：Finance Research Letters（Elsevier）**
- IF 6.9 / SJR 1.711（Q1，econometrics/financial economics/stock market 主题覆盖）；SSCI+SCIE 双收录（金融类）
- 主题先例：Kirtac & Germano (2024) "Sentiment trading with large language models" 发表于 FRL（被引 237 次）——LLM 金融情绪测量正是其范围
- 篇幅：letters 格式，现稿（33 页含附录/封面）压缩正文后量级匹配；附录可作补充材料
- 匹配逻辑：本文是"LLM 情绪信号测量审计"，落在其 predictability + measurement 交集

**备选：Economics Letters（Elsevier）**
- IF 2.0 / CiteScore 3.1；**严格限 2,000 词**，accept-as-is-or-reject 机制
- 先例：Didisheim, Fraschini & Somoza (2025)（同类审计型 letter，EL 256）
- 适配要求：须另行制作压缩 letter 版（只保留构成效应 + 交错身份两个核心发现），当前 33 页版本不适配
- 匹配逻辑：构成效应作为单点新发现（"LLM 情绪分数依赖同批复评分内容"）适合 letter 粒度

**不投**：JFE/JF/RFS（功效与样本量差距两个数量级，投之必拒）；JBF（篇幅长、周期长，匹配度不优于 FRL）。

**决策建议**：FRL 首投；若审稿意见指向"样本小"，按意见补扩窗口后转投；EL letter 版作为并行小文（把批次构成效应单独抽出）——注意两版不可重复发表同一结果，若 FRL 版已含构成效应，EL letter 版须撤回该想法或改投不同角度。

## 三、H 回应函状态（v5.1）

原 H_revision_response.md（v3 状态）逐条对照更新：

| 原条目 | v5.1 状态 |
|---|---|
| B1 功效/MDE | ✅ v4 完成；v5.1 增交错行（聚类 SE，power 0.78） |
| B2 不可做实验声明 | 维持（跨模型/档案/人工标注环境限制） |
| C1 endpoint 稳定性 | ✅✅ **超额完成**：不仅诊断（v3），且已修复（v5 交错会话）+ 分解（v5.1 构成 vs 端点，两会话反转顺序复现） |
| C2 第三方残留 | ✅ v4 完成（5/341 真实别名口径） |
| v2→v3 更正清单 | v5 新增更正：v2 "+4.75 具名乐观先验"最终定性为**符号错误**（会话漂移掩盖的负向先验）；v4 "约 1 点"升级为 −2.82（交错确证） |
| 投稿就绪度 | v3 时估 90–95%；v5.1 实际复核后维持 95% 级（剩余 5% 为格式适配与文字打磨） |

## 四、Cover Letter（FRL 版，v6 更新，随投稿提交）

---

Dear Editors,

We submit "Dissecting LLM News Sentiment Scores: Identity Priors, Batch Composition, Scoring Noise, and Price Echoes in Return Predictability" for consideration in Finance Research Letters.

A fast-growing literature treats LLM sentiment scores on news headlines as return predictors. The premise—that the score is a function of the text—has been challenged channel by channel (identity effects in-sample, memorization in-window, model variability). What has been missing is a joint measurement audit on one frozen corpus, out of sample, under a common inference standard. That is our contribution, and it produced findings we did not expect when we began.

On 341 headlines covering 36 U.S. large-caps (July–October 2026, post-cutoff), scored under conditions that each vary one ingredient of the measurement—identity visible, removed, or swapped to a different firm; repeat calls; controlled batch composition; temperature-zero decoding; and the Loughran–McDonald dictionary—we document five channels jointly: (i) the headline predictability statistic is borderline and *draw-dependent*—re-scoring the identical headlines fourteen times moves the t-statistic between 1.5 and 2.1; (ii) firm identity shifts score *levels* by about three points (a mild pessimism prior, confirmed by an interleaved design and an identity-swap control) without shifting predictive content; (iii) the score depends on *which other headlines share its API batch*—re-batching alone moves levels by 3.6 points, a channel that, to our knowledge, has not previously been quantified in finance, that survives run-order inversion, and whose downstream costs we trace: slopes and cross-sectional ranks are untouched, but a fixed score threshold doubles its trade count; (iv) predictive loading directionally concentrates in headlines that describe already-realized price moves; and (v) coverage itself is selected on realized volatility.

The paper's methodological signature is that it audits itself in sequence: its own first pass reported an identity effect of the opposite sign, and the pre-specified repair experiments (interleaved re-fielding, run-order inversion, seeded re-batching, identity-swap and decoding controls) corrected it. Every number is reproducible from an archived replication package with 183 automated numerical assertions; null results are reported as null results; staged confirmatory contrasts are labeled outside the pre-specified family. We believe the batch-composition effect and the interleaved-design protocol are of direct interest to FRL's readership working with LLM-based text measures.

Generative-AI use disclosure: the studied scoring instrument is a large language model (GLM-4-Plus), and the research pipeline was operated with AI assistance under the author's direction, with every reported number verified against archived scripts and data. The AI system is not an author.

The paper is not under review elsewhere. All data are from public sources; the replication package accompanies the submission.

Sincerely,
Chang Tan
Dalian University of Technology
aquars43@foxmail.com

---

## 五、v6 状态（2026-10-19）

- 标题已缩短；作者改为 Chang Tan（人类作者 + 生成式 AI 使用披露，符合 Elsevier 政策）
- 摘要 198 词；全文修订日志式表述已清除并纳入 183 项断言回归网
- 新增：身份互换/中性前缀/温度0 对照（会话 5，预注册）；批次效应下游后果表；NLP 文献三角；人工标注包
- 多模型验证在本环境不可执行（API 忽略 model 参数，探测存档）——已如实披露为限制
- H4 价格回声全链降级为 directional（p=0.10, power 0.31）
