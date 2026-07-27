---
title: "AI Agent 应用开发工程师 3个月成长计划"
date: 2026-07-26
tags: [AI Agent, LangChain, LangGraph, RAG, 学习路线, Python, FastAPI, MCP, 向量数据库]
categories: [学习计划]
description: "Python后端 → AI Agent应用开发工程师的3个月系统学习计划，涵盖RAG、LangChain、MCP、FastAPI部署"
author: ZhuanZ
---

> 制定日期：2026-07-26
> 目标定位：Python后端 → AI Agent应用开发工程师（LangChain/LangGraph/RAG方向）
> 背景：211数学本科应届生 / Python后端 / 全AI托管开发经验
> 时间预算：每周10-15小时（工作日1-2小时/天 + 周末可加）
> 核心策略：用Python后端优势做底座，把AI开发的认知差做成长板，同时补上CS基础缺口


## 总览

```
        补CS基础                        建AI Agent能力
    ┌──────────────┐          ┌──────────────────────┐
    │ 数据结构算法   │          │ RAG 检索增强生成       │
    │ 网络协议      │    +     │ LangChain/LangGraph   │
    │ 数据库原理     │          │ Agent 设计模式         │
    │ 运维部署      │          │ FastAPI 微服务部署     │
    └──────────────┘          └──────────────────────┘
              ↘                    ↙
         中间产物：Prompt Engineering + 向量数据库
              ↓
         最终产物：1个AI Agent产品上线 + 10篇博客 + 简历能投
```

**每周时间分配参考**（15小时/周）：

| 板块 | 时间 | 说明 |
|------|------|------|
| CS基础（数结+网络+数据库） | 5h | 不变，面试和工程都需要 |
| Agent生态学习 | 6h | 核心技能栈 |
| 动手项目 + 博客 | 3.5h | 产出驱动学习 |
| 弹性 | 0.5h | 不可抗力缓冲 |

---

## 第一阶段：底座打好（第1-4周）

**主题："让你写出的每一行代码都有底气，同时种下Agent的种子"**

### 第1周：AI世界观建立 + 数据结构地基

> 先理解AI Agent是什么，为什么需要RAG，为什么需要LangChain——不需要写代码，先把认知拉平。

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 读一遍OpenAI官方文档的Chat Completions API部分，理解System Prompt、Temperature、Token概念 | 笔记 | 1.5h |
| 二 | 读RAG论文核心思想（原始论文: Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks，读摘要+图表+结论就行），了解为什么大模型需要外部知识 | 笔记 | 1h |
| 三 | 数组+链表：Python实现、增删改查复杂度、LeetCode 2-3道简单题 | 代码笔记 | 1.5h |
| 四 | 栈+队列：Python实现、单调栈概念、LeetCode 2道 | 代码笔记 | 1h |
| 五 | 理解Embedding（嵌入向量）：为什么文本可以变成向量？为什么相似的文本向量距离近？结合你线性代数知识，理解余弦相似度的几何意义 | 一篇博客草稿 | 1.5h |
| 六 | 用OpenAI API + Python写一个最简对话程序：接收用户输入→调用API→流式输出回复（10行代码就够了，但**不用AI写**） | 代码 | 2h |
| 日 | 完成第1篇博客：《为什么大模型需要"翻书"——RAG和Embedding的数学直觉》 | 发布 | 2h |

**本周关键认知**：大模型不是神，它有知识截止日期，它会幻觉。RAG就是给它一本参考书让它查，Embedding就是找到书里最相关那一页的数学工具。这些概念你数学系的人理解起来比纯CS的人快。

### 第2周：RAG跑通 + 哈希表 + HTTP

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 哈希表：Python dict底层原理、哈希冲突解决、LeetCode 2道 | 代码笔记 | 1.5h |
| 二 | HTTP协议核心：请求方法/状态码/Header/Cookie/HTTPS握手过程、RESTful设计规范 | 博客草稿 | 1.5h |
| 三 | 向量数据库选择：对比ChromaDB（轻量）、FAISS（快）、Qdrant（生产），选ChromaDB入门 | 笔记 | 1h |
| 四 | 文档分块策略：固定长度分块、语义分块、重叠窗口——这些参数怎么影响检索效果 | 实验笔记 | 1.5h |
| 五 | **动手：跑通你的第一个RAG系统**。用LangChain加载一个TXT/PDF→分块→生成Embedding→存入ChromaDB→用户提问→检索→拼接Prompt→调LLM回答 | 代码 | 1.5h |
| 六 | 继续完善RAG Demo：换不同的分块策略看效果差异，加入多轮对话记忆（ConversationBufferMemory） | GitHub项目 | 3h |
| 日 | 完成第2篇博客：《30行代码跑通RAG：从文档分块到AI回答的全链路拆解》 | 发布 | 2h |

**本周关键认知**：RAG看起来高大上，本质就三步——文档切成块→每个块变成向量存起来→用户提问时找到最相似的块喂给LLM。你上一周理解了Embedding，这周就理解了RAG。你比大多数人快的原因：你知道余弦相似度背后的线性代数。

**本周产出**：github.com/你的用户名/simple-rag 项目 + 1篇博客

### 第3周：LangChain精进 + Shell/Bash + 数据库索引原理

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | SQL强化：复杂JOIN、窗口函数（ROW_NUMBER、RANK、LAG）、子查询 | 笔记 | 1.5h |
| 二 | 数据库索引原理：B+树结构可视化理解、聚簇索引 vs 非聚簇索引、EXPLAIN分析 | 一篇博客草稿 | 1.5h |
| 三 | LangChain核心概念深化：Chain vs Agent的区别、Tool定义与调用、ReAct模式 | 笔记 | 1.5h |
| 四 | **动手：把你的RAG升级成Agent**。给RAG加上一个Tool（比如"搜索"工具或用Python REPL做计算），让LLM自己决定什么时候检索、什么时候用工具 | 代码 | 1.5h |
| 五 | Shell脚本：写一个自动化脚本，一键启动你的RAG项目（创建虚拟环境、装依赖、启动服务） | 代码 | 1h |
| 六 | Linux常用命令：文件权限、进程管理（ps/top/kill）、管道、grep/awk/sed实用场景 | 笔记 | 1.5h |
| 日 | 完成第3篇博客：《从RAG到Agent：当AI学会"查资料"之后，它还能"做事"》 | 发布 | 2h |

**本周关键认知**：RAG让LLM"查资料"，Agent让LLM"做事"。Agent = LLM + 工具 + 决策循环。LLM自己判断"我现在是应该查数据库，还是应该调用计算器，还是应该直接回答"——这就是ReAct模式。

**本周产出**：simple-rag 升级为 simple-agent + Shell脚本 + 1篇博客

### 第4周：数据结构深入 + OpenAI Function Calling + 阶段复习

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 二叉树：遍历（前中后序/层序）、递归写法、LeetCode 3道 | 代码笔记 | 1.5h |
| 二 | 二叉搜索树：插入/查找/删除、验证BST | 代码笔记 | 1h |
| 三 | OpenAI Function Calling / Tool Calling：理解JSON Schema定义、理解LLM如何选择调用哪个函数 | 实践笔记 | 1.5h |
| 四 | LangChain的Tool定义方式：@tool装饰器、StructuredTool、Tool参数校验 | 代码 | 1h |
| 五 | 事务与锁：ACID、隔离级别、MVCC概念理解 | 笔记 | 1.5h |
| 六 | 阶段复习：手写链表/栈/队列/哈希表/二叉树的所有代码，不查资料；重新跑通RAG+Agent的完整流程 | 复习 | 3h |
| 日 | 第1-4周内容总复习 + GitHub项目README完善（中英双语、架构图、运行截图） | 文档 | 2h |

**本周产出**：simple-agent项目README完善 + 数据结构和RAG核心概念可盲写

**第一阶段检查清单：**
- [ ] 用OpenAI API（或国产大模型API）跑通过对话和流式输出
- [ ] 从零实现过RAG系统（文档加载→分块→Embedding→检索→回答）
- [ ] 给RAG加过至少1个Tool，变成了Agent
- [ ] 理解LLM Function Calling的JSON Schema协议
- [ ] 能用Python手写链表/栈/队列/哈希表/二叉树
- [ ] 能解释HTTP请求的全过程
- [ ] 能看EXPLAIN输出并判断索引用对没有
- [ ] GitHub有1个Agent项目（simple-agent）
- [ ] 发布了3篇技术博客

---

## 第二阶段：Agent深水区（第5-8周）

**主题："从跑通Demo到写出能上线的Agent服务"**

### 第5周：FastAPI + Agent微服务化 + 图与DP入门

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | FastAPI入门：路径参数、查询参数、请求体、依赖注入 | 代码 | 1.5h |
| 二 | FastAPI + Agent集成：把上阶段写的Agent封装成一个POST /chat端点，接收消息，调用Agent，返回结果 | 代码 | 1.5h |
| 三 | 图论基础：邻接表/邻接矩阵、BFS/DFS、LeetCode 2道 | 代码笔记 | 1.5h |
| 四 | 流式输出（SSE）：让Agent的回答一个字一个字流给前端，而非等全部生成完 | 代码 | 1.5h |
| 五 | 动态规划入门：斐波那契→爬楼梯→硬币找零，重点理解"状态转移方程" | LeetCode笔记 | 1.5h |
| 六 | **动手：把一个Agent服务完整部署**。FastAPI + Docker + docker-compose，跑在本地→用Postman/curl测试 | GitHub项目 | 3h |
| 日 | 完成第4篇博客：《Agent + FastAPI + Docker：15分钟把你的AI助手变成API服务》 | 发布 | 2h |

**本周产出**：agent-api-service 项目 + 1篇博客 + FastAPI+Docker可独立使用

### 第6周：高级RAG策略 + TCP网络深入 + SQL进阶

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 经典DP：0-1背包、最长公共子序列、LeetCode 2道 | LeetCode笔记 | 1.5h |
| 二 | TCP协议深入：三次握手四次挥手、滑动窗口、拥塞控制——用"状态图"理解为什么可靠 | 博客草稿 | 1.5h |
| 三 | 高级RAG 1：查询改写（Query Rewriting）——用户问的模糊，Agent先帮他改写清楚再去检索 | 代码实验 | 1.5h |
| 四 | 高级RAG 2：混合检索（Hybrid Search）——向量检索+关键词检索（BM25），互补短板 | 代码实验 | 1.5h |
| 五 | SQL进阶：联合索引+覆盖索引+索引下推+慢查询优化 | 实验笔记 | 1.5h |
| 六 | 把高级RAG策略（查询改写+混合检索）集成到上周的Agent API服务中，对比效果提升 | 代码 | 3h |
| 日 | 完成第5篇博客：《向量+关键词双管齐下：RAG检索效果翻倍的工程实践》 | 发布 | 2h |

**本周产出**：Agent API服务升级（高级RAG） + 1篇博客

### 第7周：MCP（Model Context Protocol）+ LangGraph多Agent编排

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | MCP协议概念：Model Context Protocol是什么，为什么重要。它类比USB-C——让不同AI应用统一接入外部工具和数据 | 笔记 | 1.5h |
| 二 | 搭建一个最简单的MCP Server：Python SDK，暴露一个工具（比如"查询天气"），让Claude/ChatGPT能调用它 | 代码 | 1.5h |
| 三 | 堆的基本操作、堆排序、TopK问题（LeetCode 3道） | 代码笔记 | 1.5h |
| 四 | LangGraph入门：状态图（StateGraph）、节点（Node）、边（Edge）、条件路由 | 代码 | 1.5h |
| 五 | 用LangGraph实现一个多步骤Agent：先检索→如果信息不够→调用搜索工具→整合回答→如果用户不满意→重新检索 | 代码 | 1.5h |
| 六 | 对比：ReAct Agent（单轮决策）vs LangGraph Agent（多步状态机），各自适用场景 | 代码+笔记 | 3h |
| 日 | 完成第6篇博客：《MCP为什么是AI的USB-C协议——以及如何写一个MCP Server》 | 发布 | 2h |

**本周产出**：1个MCP Server + LangGraph Demo + 1篇博客

### 第8周：多Agent协作 + 阶段复习与编码强化

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 多Agent概念：为什么需要多个Agent？一个Agent调数据，一个Agent写代码，一个Agent做质检——类比"一个团队" | 笔记 | 1.5h |
| 二 | 用LangGraph实现一个多Agent系统：RetrieverAgent(查资料) + CoderAgent(写代码) + ReviewerAgent(检查) | 代码 | 1.5h |
| 三 | 算法回顾：第5-8周所有数据结构代码盲写一遍 | 手写代码 | 1.5h |
| 四 | Agent回顾：RAG→单Agent→MCP→LangGraph→多Agent，完整链路梳理 | 笔记 | 1.5h |
| 五 | FastAPI回顾：路径操作、中间件、后台任务、异常处理 | 代码 | 1.5h |
| 六 | **综合练习**：设计一个"客服Agent"方案。（用户提问→意图识别Agent→路由到知识库Agent或工单Agent→多轮追问→给出答案或创建工单）画出架构图+写出核心代码骨架 | 设计文档+代码 | 3h |
| 日 | 完成第7篇博客：《2个月，从Python后端到多Agent系统——我的AI应用开发学习报告》 | 发布 | 2h |

**本周产出**：多Agent Demo + 客服Agent设计方案 + 1篇博客

**第二阶段检查清单：**
- [ ] FastAPI + Agent 微服务完整跑通（含流式输出和Docker部署）
- [ ] 实现了查询改写和混合检索等高级RAG策略
- [ ] 搭建过一个MCP Server
- [ ] 用LangGraph实现过多节点多条件的Agent流程
- [ ] 理解并实践过多Agent协作
- [ ] 能解释TCP为什么可靠、三次握手每次的作用
- [ ] 能设计联合索引解决慢查询
- [ ] LeetCode累计刷题40+道
- [ ] GitHub有3+个Agent相关项目
- [ ] 发布了7篇技术博客

---

## 第三阶段：从学习者到构建者（第9-12周）

**主题："完整交付一个能上线、能演示、能写进简历的AI Agent产品"**

### 第9周：综合项目启动——企业知识库智能助手

> 选这个项目的原因：和你现有的CRM系统直接相关，可以类比为企业内部知识库问答Agent。你理解业务场景，开发起来事半功倍。

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 项目需求设计：企业知识库Agent——支持上传内部文档（PDF/Word/Markdown），员工提业务问题，Agent检索内部文档+联网搜索结合回答，找不到就流转人工 | PRD文档 | 1.5h |
| 二 | 项目架构设计：FastAPI后端 + ChromaDB向量库 + Redis会话缓存 + Nginx反向代理 + 简单HTML前端。画架构图 | 架构文档 | 1.5h |
| 三 | 后端骨架搭建：FastAPI项目结构（路由拆分、配置管理、日志、异常处理） | 代码 | 1.5h |
| 四 | 知识库模块Day1：文档上传API、文件解析（用LangChain的Document Loader支持PDF/Word/MD） | 代码 | 1.5h |
| 五 | 知识库模块Day2：文档分块+Embedding生成+存入ChromaDB | 代码 | 1.5h |
| 六 | 知识库模块Day3：检索API、查询改写、混合检索、重排序 | 代码 | 3h |
| 日 | 前后端联调：用Postman测通整套流程（上传文档→检索→LLM回答），发现Bug当天修 | 测试+修复 | 2h |

**本周产出**：综合项目后端80%完成

### 第10周：综合项目核心功能 + 部署上线

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 对话模块Day1：多轮对话（会话管理、上下文窗口、历史记录存入Redis） | 代码 | 1.5h |
| 二 | 对话模块Day2：流式输出（SSE）、引用来源标注（答案中标注来自哪些文档） | 代码 | 1.5h |
| 三 | Agent决策模块：知识库搜不到→联网搜索（Tavily/SerpAPI），基于置信度决定是回答还是转人工 | 代码 | 1.5h |
| 四 | 前端页面：用纯HTML+CSS+JS写一个聊天界面（消息列表、输入框、流式显示、来源标注），不追求好看，能跑就行 | 代码 | 1.5h |
| 五 | Docker化：写Dockerfile和docker-compose.yml（FastAPI + ChromaDB + Redis），本地一键启动 | 代码 | 1.5h |
| 六 | **部署上线Day1**：买一台便宜的云服务器（腾讯云/阿里云轻量，约50元/月），装Docker，把项目部署上去，配Nginx + 域名 + HTTPS（Let's Encrypt免费证书） | 部署 | 3h |
| 日 | 完成第8篇博客：《从零到上线：一个企业知识库AI Agent的完整搭建过程》 | 发布 | 2h |

**本周产出**：综合项目100%完成并上线（有可访问URL）+ 1篇博客

### 第11周：产品打磨 + Dify/Coze低代码工具栈

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 项目Bug修复：根据自己测试的体验，修复3-5个明显的问题 | 代码 | 1.5h |
| 二 | 性能优化：检索速度优化（索引预热、批量化Embedding）、大文档处理优化 | 代码 | 1.5h |
| 三 | Dify入门：用Dify搭建一个跟你的项目相同功能的知识库Agent——对比"低代码搭建（10分钟）"和"代码搭建（10周）"的体验差异 | 实验笔记 | 1.5h |
| 四 | Coze入门：用Coze搭建同样功能的Agent——理解平台类Agent的优缺点 | 实验笔记 | 1.5h |
| 五 | 对比分析：Dify/Coze vs 自研Agent的适用场景——什么时候用平台、什么时候自己写、各自成本 | 一篇博客草稿 | 1.5h |
| 六 | 算法冲刺：LeetCode热题各专题刷2-3道（数组/链表/树/DP/哈希/栈） | 代码 | 3h |
| 日 | 完成第9篇博客：《同功能Agent，Dify搭建10分钟 vs 我手写10周——低代码和自研的真实对比》 | 发布 | 2h |

**本周产出**：项目优化 + Dify/Coze实操经验 + 1篇博客

### 第12周：面试准备 + 副业方向定型 + 简历投出去

| 日 | 内容 | 产出 | 时长 |
|----|------|------|------|
| 一 | 简历重写：突出AI Agent项目、全AI托管开发经验（转述为"LLM辅助工程化开发"）、数学背景 | 新简历 | 2h |
| 二 | 面试准备1：AI Agent技术面自测（RAG原理、LangChain核心概念、LLM推理流程、Agent设计模式） | 面试笔记 | 1.5h |
| 三 | 面试准备2：CS基础50题自测（网络、数据库、数据结构），每个方向随机抽5题口头回答 | 面试笔记 | 1.5h |
| 四 | 面试准备3：行为面试——"你的全AI开发经验对我这个岗位有什么价值"——准备一个3分钟的自我陈述 | 自述稿 | 1h |
| 五 | 副业方向定型：基于你现在的Agent开发能力，脑暴3个微型SaaS点子——（1）客服知识库Agent（2）文档智能问答（3）企业内部的"AI助手工作台"。选一个开始搭MVP骨架 | 产品构思文档 | 1.5h |
| 六 | MVP Day1：选定一个副业方向，搭建Django/FastAPI骨架，跑通核心流程 | 代码 | 3h |
| 日 | 完成第10篇博客：《3个月从CRUD后端到AI Agent开发者——一份有项目有博客的真实复盘》 | 发布 | 2h |

**本周产出**：新简历 + 面试自述 + 副业MVP骨架 + 1篇总结博客

**第三阶段检查清单：**
- [ ] 企业知识库Agent完整上线（有域名、有HTTPS、能演示）
- [ ] 体验过Dify/Coze搭建同功能Agent
- [ ] LeetCode累计刷题50+道
- [ ] 10篇原创技术博客（掘金/知乎）
- [ ] GitHub有5+个项目，其中至少3个Agent相关
- [ ] 简历准备好，至少能投3个方向（AI应用开发/Agent开发/高质量Python后端）
- [ ] 选定了1个副业产品方向并开始搭建

---

## 学习过程中最关键的原则

### 关于AI工具的使用

这个计划的核心矛盾是——你要学会AI Agent开发，但又要避免重蹈"全AI托管"的覆辙。规则很简单：

**可以用AI的场景**：帮你解释报错信息、帮你生成测试数据、帮你对比两个库的API差异。

**不准用AI的场景**：从零写核心业务逻辑、写数据结构实现代码、写博客的主体内容。这三样东西你一旦让AI代劳，就又回到了"能交付但理解不透"的死循环。写完代码后可以给AI Review，但必须先自己写。

### 关于你已有的工作

你现在做的CRM系统其实可以成为你项目的演练场——比如第9周做的企业知识库Agent，你可以私下把你们公司的产品文档喂进去，做一个内部版本，跟你的工作直接关联。这样你的"8小时工作"和"2小时学习"就有了交集，效率翻倍。

### 关于博客

10篇博客听起来多，实际上就是每周一篇。不要追求完美，追求"真实记录"。你的叙事定位是"数学系应届生转AI应用开发"，这个身份本身就是差异化——全网很少有人从数学和Agent两个角度同时讲技术。

### 如果坚持不下来

如果某天只有30分钟，就找一个LangChain官方文档的代码示例跑一遍。

如果某天完全不想学，就打开Dify，拖拽搭建一个Agent玩玩。

如果某一周崩了，跳过那一周继续，不要等"下个月重来"。这三个月不是KPI考核，是给自己建立一套新的学习和交付习惯。

---

## 附录A：推荐学习资源（Agent方向）

### 核心框架

| 资源 | 说明 | 优先级 |
|------|------|--------|
| [LangChain官方文档](https://python.langchain.com/) | 核心框架文档，代码示例丰富 | ⭐⭐⭐ |
| [LangGraph官方文档](https://langchain-ai.github.io/langgraph/) | Agent编排的核心，比LangChain更值得学 | ⭐⭐⭐ |
| [OpenAI API文档](https://platform.openai.com/docs/) | Function Calling、Assistants API | ⭐⭐⭐ |
| [FastAPI官方文档](https://fastapi.tiangolo.com/) | REST API最佳实践 | ⭐⭐⭐ |

### GitHub优质仓库（跟着学）

| 仓库 | 说明 |
|------|------|
| [agent-craft](https://github.com/Annyfee/agent-craft) | AI Agent教学仓库，LangChain+RAG+LangGraph+MCP全栈代码 |
| [ai-agent-langgraph](https://github.com/kevinten-ai/ai-agent-langgraph) | 从零到生产的Agent Platform学习路线 |
| [ai-agents-from-zero](https://github.com/XingJi-love/ai-agents-from-zero) | 2026最系统的AI Agent速成指南，含面试题库 |
| [agent-rag-study](https://github.com/RudyGo8/Agent_Rag_Study) | 黑马程序员的Agent+RAG系统学习资料 |

### MCP

| 资源 | 说明 |
|------|------|
| [MCP官方文档](https://modelcontextprotocol.io/) | MCP协议规范和Python SDK文档 |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | 官方Python实现 |

### 低代码Agent平台

| 平台 | 说明 |
|------|------|
| [Dify](https://dify.ai/) | 开源LLM应用开发平台，RAG+Agent可视化搭建 |
| [Coze（扣子）](https://www.coze.com/) | 字节跳动出品，插件生态丰富 |

### CS基础（不变）

| 方向 | 推荐资源 |
|------|----------|
| 数据结构与算法 | [代码随想录](https://programmercarl.com/)、《Hello 算法》（开源动画书） |
| 网络协议 | 《网络是怎么连接的》（户根勤）、小林coding图解网络 |
| 数据库 | 《MySQL是怎样运行的》（小孩子4919）、Use The Index, Luke! |
| Linux/Docker | Docker官方Get Started教程、实战中查《鸟哥》（当手册） |

### 模型API接入（国产替代方案，省钱）

由于OpenAI API需要外币卡且单价不低，学习阶段建议用国产大模型替代：

| 平台 | 模型 | 兼容性 |
|------|------|--------|
| 硅基流动(SiliconFlow) | DeepSeek-V3、Qwen等 | 兼容OpenAI SDK，注册送额度 |
| 智谱AI | GLM-4 | 兼容OpenAI SDK |
| DeepSeek | DeepSeek-V3/R1 | 自有SDK，价格极低 |
| 阿里百炼 | 通义千问 | 兼容OpenAI SDK |

建议先用硅基流动或DeepSeek的免费额度跑完前期学习，生产环境再切换。

---

## 附录B：每周博客选题（Agent方向版）

| 周 | 博客主题 | 关键词 |
|----|----------|--------|
| 1 | 为什么大模型需要"翻书"——RAG和Embedding的数学直觉 | Embedding、余弦相似度、RAG |
| 2 | 30行代码跑通RAG——从文档分块到AI回答的全链路拆解 | LangChain、ChromaDB、文档检索 |
| 3 | 从RAG到Agent——当AI学会"查资料"之后，它还能"做事" | Agent、Tool Calling、ReAct |
| 5 | Agent+FastAPI+Docker——15分钟把你的AI助手变成API服务 | 微服务部署、流式输出、SSE |
| 6 | 向量+关键词双管齐下——RAG检索效果翻倍的工程实践 | 混合检索、查询改写、重排序 |
| 7 | MCP为什么是AI的USB-C协议——以及如何写一个MCP Server | MCP、协议标准、工具接入 |
| 8 | 2个月Agent学习复盘——从Python后端到多Agent系统 | 学习总结、技术路线 |
| 10 | 从零到上线——一个企业知识库AI Agent的完整搭建过程 | 项目实战、Nginx、HTTPS |
| 11 | 同功能Agent，Dify搭建10分钟 vs 手写10周——低代码和自研的真实对比 | Dify/Coze、工程选型 |
| 12 | 3个月从CRUD后端到AI Agent开发者——有项目有博客的真实复盘 | 职业转型、学习路径 |

---

## 附录C：三个月的GitHub可能是这样的

```
第4周：
  ├── simple-rag/               ⭐ 15+ stars  （第一个RAG系统）
  ├── simple-agent/              ⭐ 20+ stars  （升级为Agent）
  └── agent-startup-script/      Shell脚本

第8周：
  ├── agent-api-service/         ⭐ 30+ stars  （FastAPI+Agent微服务）
  ├── mcp-server-demo/           ⭐ 25+ stars  （MCP Server）
  └── multi-agent-demo/          ⭐ 20+ stars  （LangGraph多Agent）

第12周：
  ├── enterprise-knowledge-agent/  ⭐ 80+ stars  （综合项目）
  ├── dify-vs-code-agent-compare/  对比实验
  └── side-project-mvp/            副业MVP骨架
```

**涨星技巧**：每篇博客末尾放GitHub链接；每个项目README必须包含架构图（用Mermaid画，GitHub原生渲染）和运行截图；标题用英文但README写中英双语。

---

## 附录D：这份计划比上一份好在哪

上一份计划选的是"AI数据工程师"方向，问题在于——它的终点和你的起点之间没有直接联系。你在做CRM，你在做Python后端，你在用AI工具，但数据工程师的工作是写SQL、跑Spark、做ETL管道，跟你每天做的事隔了很远。

这份Agent计划的核心优势：**你现在的全AI托管开发经验，在这个范式里是"领先认知"而不是"需要掩盖的短板"**。你理解LLM怎么用、怎么调Prompt、怎么让AI产出代码——这些在Agent开发里都是核心技能。你不是"什么都不会"，你是"会的那些刚好对路，但地基没打牢"。这份计划用每周同时学CS基础和Agent技能的方式，把地基和上层建筑一起建。

三件事每天提醒自己：

1. **你数学好** → 理解Embedding和向量检索比别人快，把这当武器
2. **你AI用的多** → 理解LLM的边界和提示词设计是Agent开发的核心能力
3. **你缺的是基础** → 每天花1/3时间补CS基础，补一天就少一个面试盲区

---

*最后更新：2026-07-26*
*核心思想：把"全AI开发"从短板变成长板——你不是被AI替代的人，你是让AI为别人工作的人。*
