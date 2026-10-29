# JoF Submission Package — 使用说明（投稿槽位对应）

**目标期刊：** *Journal of Forecasting*（Wiley）
**投稿入口：** https://authors.wiley.com/journal/for （Wiley Authors 门户，注册/登录后选择 Journal of Forecasting）
**费用状态（2026-10-29 官方页面核验）：** "This journal does not charge submission fees." — 无投稿费；订阅路线发表免费，OA 为可选项（仅选择 OA 才有 APC）。
**评审模式：** 单盲（题目页含作者信息，直接放在手稿第 1 页，无需匿名化稿件）。

## 投稿系统文件槽位对照

| 投稿系统槽位 | 上传的文件 |
|---|---|
| Manuscript（主文件） | `Dissecting_LLM_Sentiment_JoF_Manuscript.pdf`（27 页；题目页=第 1 页，含作者信息 + 数据可得性/资助/利益冲突/AI 使用声明） |
| Supporting Information（补充材料） | `Dissecting_LLM_Sentiment_JoF_Supporting_Information.pdf`（18 页 Online Appendix，附录 A–K） |
| Cover Letter | `cover_letter_JoF.md`（粘贴到信件栏或按系统提示上传） |
| （系统如需）Declarations | `declarations_JoF.md`（资助/COI/数据可得性/AI 使用/作者贡献/伦理，供填表参考） |

**LaTeX 源码：** `source/` 内含全部 tex 源（`main.tex`、`online_appendix.tex`、`sections/`）。Wiley Free Format 初审只传 PDF 即可；录用后生产阶段再按要求提交源文件。

## 手稿格式要点（Free Format，均已满足）

- 题目页（手稿第 1 页）含：题目、作者、单位、邮箱、摘要、JEL、关键词、数据与代码可得性、生成式 AI 使用、利益冲突与资助声明 —— Wiley Free Format 要求的全部要素
- 摘要含全部关键数字（t=2.10、q=0.062、+2.6 [1.1, 4.1]、3.6、ICC 0.92、30%、p=0.10、t=2.76）
- 参考文献：任意一致格式均可（现为 author–year / natbib，与刊最终格式差异由生产阶段处理）
- 图片 300+ dpi 已嵌入；表格为可编辑文本
- 无未解析引用（"??" 零）；正文仅引用文献列表中出现的一处 Finance Research Letters（Kirtac & Germano 2024，属正常文献引用，非投稿痕迹）

## 作者侧待办（投稿前确认）

1. **ORCID**：Wiley 门户要求通讯作者绑定 ORCID（无则先在 orcid.org 注册）
2. **邮箱**：aquars43@foxmail.com 用于投稿通讯，请确认
3. **资助/COI 两句**：声明文字沿用 v6.5 已核版本（无资助、无利益冲突），如有变化告知修改
4. **OA 选择**：投稿阶段只标注偏好，录用后再最终选择；**选择订阅路线则全程零费用**
5. 投稿前可复查期刊现行说明（For-Authors 页）以防政策更新：https://onlinelibrary.wiley.com/page/journal/1099131x/homepage/ForAuthors.html

## 包内清单

```
Dissecting_LLM_Sentiment_JoF_Manuscript.pdf          27 页手稿（题目页=第1页）
Dissecting_LLM_Sentiment_JoF_Supporting_Information.pdf  18 页 Online Appendix
cover_letter_JoF.md                                   投稿信
declarations_JoF.md                                   声明（填表参考）
README_JoF_Submission.md                              本说明
source/                                               LaTeX 源码（main + OA + sections）
```
