---
layout: post
title: TURBO码和LDPC码
categories: [通信, 信道编码]
description: 基础的信道编码
keywords: 通信, 信道编码
mermaid: false
sequence: false
flow: false
mathjax: true
mindmap: false
mindmap2: false
---

## 信道编码基础

前文介绍了**重复码**、**奇偶校验码**、**汉明码**和**卷积码**等基础信道编码方法，并结合 MATLAB 示例演示了各自的编码与译码过程。

本文将介绍 **TURBO** 和 **LDPC** 两种在4G和5G中广泛应用的前向纠错码。

以下将先介绍一些基础通信理论。

### 香农极限公式

香农信道容量公式（Shannon Capacity）：

$$
C=B \cdot \log _2\left(1+\frac{S}{N}\right)
$$

其中：

- 𝐶：信道容量（bit/s），即单位时间内可靠传输的最大信息速率
- 𝐵：信道带宽（Hz）
- 𝑆/𝑁：信噪比（功率比）

**描述了在给定带宽和信噪比下通信系统的理论极限传输速率**。超过该速率将无法实现无错传输。

### 与码率的关系（Eb/N0 形式）

我们关心的是在**单位比特能量**（𝐸𝑏）和**噪声功率谱密度**（𝑁0）下的表现：

目标是从香农公式推出**误码性能相关的 Eb/N0 极限表达式**。

推导过程如下：

- 比特速率与带宽关系：

$$
R=\frac{C}{B} \Rightarrow C=R \cdot B
$$

- 代入香农公式

$$
R \cdot B=B \cdot \log _2\left(1+\frac{S}{N}\right) \Rightarrow R=\log _2\left(1+\frac{S}{N}\right)
$$

- 引入 Eb/N0：

  - 平均每比特能量为 $$E_b=\frac{S}{R}$$
  - 单位噪声功率谱密度 $$N_0=\frac{N}{B}$$
  - 因此：
  
$$
\frac{E_b}{N_0}=\frac{S}{N} \cdot \frac{1}{R} \Rightarrow \frac{S}{N}=R \cdot \frac{E_b}{N_0}
$$

- 代入香农公式并变换：

$$
R=\log _2\left(1+R \cdot \frac{E_b}{N_0}\right) \Rightarrow 2^R=1+R \cdot \frac{E_b}{N_0} \Rightarrow \frac{E_b}{N_0}=\frac{2^R-1}{R}
$$

## Turbo码

### 概述

Turbo码由 Claude Berrou 等人于 1993年提出，是一种接近**香农极限性能**的**纠错编码**，被称为信道编码领域的里程碑。

- 采用并行级联卷积编码结构；
- 解码采用软输入软输出迭代译码算法；
- 可逼近理论极限误码性能。
