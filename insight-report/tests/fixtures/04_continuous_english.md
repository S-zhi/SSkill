# 认知报告 · 跨语言表达的信息损耗

<p class="meta">来源：抖音口播 · 单播 · 2026-01-08</p>

> 中心思想：专业术语强行翻译成中文，有时反而增加理解成本。

## 一、核心提炼

**要点**
- 像 microservices、eventualconsistency、backpressure 这类术语，保留英文原词往往比生造中文译名更少歧义。
- 连续英文长串示例：thisisaverylongcontinuousenglishrunwithoutanyspacesinbetweenwordstotestwordbreakandoverflowwrapbehavioracrosslinesandpages。

**分区一览**

| 分区 | 标签 | 一句话 |
|---|---|---|
| Coding 经验 | <span class="tag">Coding</span> | 术语翻译不是越"中文"越好 |

## 二、精华原文

<div class="excerpt">
他说 eventual consistency 这个词，你要是翻译成"最终一致性"，第一次听的人根本不知道在说什么，还不如直接说 eventualconsistency，反而讲清楚了它是一个专有名词，而不是一个随便的中文形容词组合，比如像这样连写一长串thisisanotherlongenglishrunembeddedinsidechinesetexttostresstestthefontfallbackandlinewrappingpath也不会打断中文阅读的节奏。
</div>

## 三、印证与批判

一句话总结：术语保留原文，有时比翻译更利于准确沟通。

> "Simplicity is the ultimate sophistication." —— 常被归于达·芬奇

正向来看，技术社区里保留英文术语确实降低了查阅原始文档时的匹配成本。

<div class="critique">
批判：口播没有区分"面向工程师的内部沟通"和"面向大众的科普内容"，后者过度保留英文术语反而会提高理解门槛，一刀切并不合适。
</div>

<div class="rating">
  <span class="rating-title">我的评级：</span>
  <span class="box"><span class="checkbox"></span>认同</span>
  <span class="box"><span class="checkbox"></span>不认同</span>
</div>

## 四、延伸应用

### 工程实践
- 内部文档里专有名词保留英文，仅在首次出现时括注中文解释，如 backpressure（背压）。
