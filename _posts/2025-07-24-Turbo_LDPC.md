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

## 一、信道编码基础

前文介绍了**重复码**、**奇偶校验码**、**汉明码**和**卷积码**等基础信道编码方法，并结合 MATLAB 示例演示了各自的编码与译码过程。

本文将介绍 **TURBO** 和 **LDPC** 两种在4G和5G中广泛应用的前向纠错码。

以下将先介绍一些基础通信理论。

### 1. 奈奎斯特采样定理

要完整、无失真地采样一个信号，**采样频率**必须至少是信号中最高频率的两倍。

在无线通信或有线通信中，奈奎斯特定理也用于决定：

**在某个带宽范围内最多能传多少比特/秒？**

✅ 奈奎斯特码元速率（Nyquist symbol rate）：

在**无码间干扰**（ISI）的理想情况下，最大码元率 = 2 × 带宽

即：

**在带宽为 B Hz 的信道中，每秒最多可以无失真地传 2B 个码元（symbols）。**

### 2. 香农极限公式

香农信道容量公式（Shannon Capacity）：

$$
C < B \cdot \log _2\left(1+\frac{S}{N}\right)
$$

其中：

- 𝐶：信道容量（bit/s），即单位时间内可靠传输的最大信息速率
- 𝐵：信道带宽（Hz）
- 𝑆/𝑁：信噪比（功率比）

**描述了在给定带宽和信噪比下通信系统的理论极限传输速率**。超过该速率将无法实现无错传输。

### 3. 与码率的关系（Eb/N0 形式）

我们关心的是在**单位比特能量**（𝐸𝑏）和**噪声功率谱密度**（𝑁0）下的表现：

目标是从香农公式推出**误码性能相关的 Eb/N0 极限表达式**。

推导过程如下：

- 定义 $$R$$ 为信道比特率（bit/s）：

$$
R = C
$$

- 代入香农公式

$$
R < B \cdot \log _2\left(1+\frac{S}{N}\right)
$$

- 引入 Eb/N0：

  - 平均每比特能量为 $$E_b=\frac{S}{R}$$
  - 单位噪声功率谱密度 $$N_0=\frac{N}{B}$$
  - 因此：
  
$$
\frac{E_b}{N_0}=\frac{S}{R} \cdot \frac{B}{N} \Rightarrow \frac{S}{N}=\frac{R}{B} \cdot \frac{E_b}{N_0}
$$

- 代入香农公式并变换：

$$
R<B\log _2\left(1+\frac{R}{B} \cdot \frac{E_b}{N_0}\right)
$$

- 定义带宽归一化速率（即频谱效率）

$$
R_l=\frac{R}{2 B}
$$

- 于是得到：

$$
2R_l<\log _2\left(1+2R_l \cdot \frac{E_b}{N_0}\right)
$$

- 整理得到**香农极限计算公式**：

$$
\frac{E_b}{N_0}>\frac{2^{2 R_l}-1}{2 R_l}
$$

香农极限表示了在 AWGN 信道中实现可靠通信所需的最小 𝐸𝑏/𝑁0（每比特信噪比）门限.

可以计算得到 1/2 归一化频谱效率下的香农极限为 0 dB。

而当频谱效率趋近于 0（即**码率远小于带宽**）时，香农极限趋于理论下限 -1.59 dB。

这表明：**即便采用无限低速率传输，每个比特的能量也不能低于该极限**，这是任何数字通信系统都无法逾越的物理界限。

## 二、Turbo码

### 1. 概述

Turbo码由 Claude Berrou 等人于 1993年提出，是一种接近**香农极限性能**的**纠错编码**，被称为信道编码领域的里程碑。

- 采用并行级联卷积编码结构；
- 解码采用软输入软输出迭代译码算法；
- 可逼近理论极限误码性能（1/2码率下，其性能距离 Shannon 极限仅约 0.7 dB）；
- 解决传统卷积码在低信噪比下性能不佳的问题；
- 引领现代纠错编码体系的发展，促进 3G/4G/5G 等系统演进。

### 2. 系统码与非系统码

| 项目    | 系统码                      | 非系统码                     |
| ----- | ------------------------ | ------------------------ |
| 定义    | 原始信息比特 **直接出现在输出码字中**    | 原始信息不直接出现，仅存在于编码后新的冗余比特中 |
| 结构特征  | 保留原始输入比特，添加校验比特          | 所有输出比特均由编码器结构组合生成        |
| 信息保留性 | ✅ 保留原始数据                 | ❌ 不保留                    |

#### (a) 经典非系统码结构（Classical Non-Systematic Code）

![非系统码](/images/2025-07-24-Turbo_LDPC/非系统码.jpg)

上图给出一个经典非系统码的例子，其特点如下：

- ✅ 前馈结构（Feedforward）：编码器结构只依赖当前及过去输入，无内部状态反馈；
- ❌ 无记忆性：编码器输出仅依赖于当前输入，不能形成迭代反馈链路；

其时域表达式为：

$$
\begin{gathered}
x_k=d_k+d_{k-1}+d_{k-2}+d_{k-3}+d_{k-4} \\
y_k=d_k+d_{k-4}
\end{gathered}
$$

生成多项式：

$$
\begin{gathered}
g_x(D)=1+D+D^2+D^3+D^4 \\
g_y(D)=1+D^4
\end{gathered}
$$

输出的多项式乘法表达式也可以写为：

$$
\begin{gathered}
x(D)=d(D) \cdot g_x(D) \\
y(D)=d(D) \cdot g_y(D)
\end{gathered}
$$

#### (b) 递归系统码（Recursive Systematic Code, RSC）

RSC 是 Turbo 码中采用的编码器结构，如下图所示：

![递归系统码](/images/2025-07-24-Turbo_LDPC/递归系统码.jpg)

其有以下特性：

- ✅系统性：编码器输出中包含原始输入比特（称为系统比特）
- ✅递归性：编码器中包含反馈路径，输出依赖于当前输入和以往状态

相比非系统前馈码，RSC 编码器具有“记忆性”

其中 $$a_k$$ 项为：

$$
a_k=d_k+a_{k-1}+a_{k-2}+a_{k-3}+a_{k-4}
$$

- 说明：当前系统比特不仅取决于当前输入$$d_k$$，还受到前几位编码输出反馈影响。

由此 $$d_k$$ 可表示为：

$$
d_k=a_k+a_{k-1}+a_{k-2}+a_{k-3}+a_{k-4}
$$

多项式表示：

$$
d(D)=a(D) \cdot\left(1+D+D^2+D^3+D^4\right)
$$

校验比特 $$y_k$$ 输出：

$$
y_k = a_k+ a_{k-4}
$$

其多项式表示：

$$
y(D)=a(D) \cdot\left(1+D^4\right)
$$

联立得到：

$$
\frac{y(D)}{d(D)}=\frac{1+D^4}{1+D+D^2+D^3+D^4}
$$

于是 Turbo 编码器的生成多项式可写为：

$$
g(D)=\left(1, \frac{1+D^4}{1+D+D^2+D^3+D^4}\right)
$$

这里的两个分量含义为：

- 第一项1：系统比特（直接输出）；
- 第二项：校验比特（经过递归滤波器处理的编码输出）。

也可以使用**八进制**记法：

$$
G_1=37, G_2=21
$$

### 3. Turbo码的并行级联结构方案

核心思想：用**两个相同的递归系统卷积编码器**（RSC）进行并行编码

如下图：

![TURBO码结构](/images/2025-07-24-Turbo_LDPC/Turbo.jpg)

#### (a) 输入输出说明

🔁 输入：

- 编码器 C₁：原始序列 $$d_k$$
- 编码器 C₂：经过交织器（Interleaver）后的序列 $$\pi(d_k)$$

🧩 输出:

- 系统位(即原始信息直接输出)：

$$
x_k=d_k
$$

- 校验位 1（基于原始序列）：

$$
y_{1 k}=C_1\left(d_k\right)
$$

- 校验位 2（基于交织后的序列）：

$$
y_{2 k}=C_2\left(\pi\left(d_k\right)\right)
$$

#### (b) 交织器（Interleaver）的作用

在两个编码器之间插入交织器，打乱输入数据顺序后再输入第二个编码器；

目的如下：

- 增强码的分集性（diversity）
- 使得两个编码器对同一比特看到**不同上下文**；
- 在译码时通过多路径冗余交织结构进行**更强纠错**；
- 提高低权重码字的最小距离等。

原生 TURBO 编码的码率为 1/3。包含一个系统位和两个校验位。

### 4. TURBO 码译码机制（简要介绍）

Turbo码之所以得名，源于它的**类涡轮增压译码结构**，通过多个子译码器之间的信息交换与反复优化，不断改进“译码输出”，最终逼近香农极限。

#### (a) 译码器结构与流程

Turbo译码器由两个**分量译码器**组成（对应两个并行RSC编码器），并通过软信息交织反馈进行多轮迭代优化。

每次迭代包括以下步骤：

1. **软输入软输出**译码器：
   - 输入：接收信号的对数似然比（LLR）
   - 输出：对每个比特估计的新LLR
2. 信息交换与交织：
   - 每个译码器将其**软输出**通过交织器/反交织器送给另一个译码器作为**先验信息**
3. **重复迭代**（典型迭代次数：4~8次）

#### (b) BCJR 算法族

BCJR 算法用于 Turbo 译码中的**软输入软输出概率计算**，其核心目标是计算比特后验概率（LLR），属于最大后验概率（MAP）方法。

常用两种实现：

- Log-MAP：
  - 精确实现 BCJR 算法的对数域版本
  - 精度高，复杂度适中
- Max-Log-MAP：
  - Log-MAP 的近似简化版本
  - 将加法 log-sum-exp 近似为最大值，降低复杂度
  - 通常译码性能略有损失，但效率更高

#### (c) 外信息交换算法

- 两个子译码器不断交换“概率信息”（软判决结果）：
  - 本轮输出 = 来自通道的观测 + 来自另一译码器的先验
- 每次迭代都能“逼近最优解”，逐渐收敛至正确码字
- 通常迭代 4~8 次就可达到较好性能（MATLAB默认 5 次）

### 5. MATLAB 仿真

#### (a) TURBO 编解码

本节评估 Turbo 编码在 AWGN 信道下的性能，并分析其在不同信噪比下的误码率表现。

TIPS：

需要根据调制阶数和码率，将Eb/N0转换为**符号信噪比**，对应的**噪声方差**产生相应**复数噪声**并叠加在调制信号上。

完整代码如下：

```matlab
clc; clear;
% 仿真参数
EbN0_dB = 0:0.1:4;        % Eb/N0范围 (dB)
numBits = 1e6;          % 每个SNR仿真的比特数
maxIter = 5;                % Turbo译码迭代次数
M = 16;
k = log2(M); 
% 初始化
ber = zeros(size(EbN0_dB));
% Turbo码参数（LTE标准中为R=1/3）
K = 6144; % 码长

for snrIdx = 1:length(EbN0_dB)
    numErrs = 0; numTotal = 0;
    EbN0 = EbN0_dB(snrIdx);
    fprintf('Simulating Eb/N0 = %.1f dB...\n', EbN0);

    while numTotal < numBits
        % ====== 1. 随机比特 ======
        dataIn = randi([0 1], K, 1);

        % ====== 2. Turbo 编码 ======
        dataEnc = lteTurboEncode(dataIn);
        
        % ====== 3. QPSK 调制 ======
%         txSymbols = 1 - 2*double(dataEnc);  % BPSK: 0 -> +1, 1 -> -1
        txSymbols = lteSymbolModulate(dataEnc,'QPSK');
        txSymbols2 = qammod(dataEnc, M, 'InputType','bit','UnitAveragePower',true);
        % ====== 4. AWGN信道 ======
        R = 1/3;                             % Turbo码率
        EsN0 = EbN0 + 10*log10(k/3);         % 转换到Es/N0
        SNR = 10^(EsN0/10);
        noiseVar = 1/(2*SNR);
        noise = sqrt(noiseVar) * (randn(size(txSymbols)) + 1i*randn(size(txSymbols)));
        rxSymbols = awgn(txSymbols,EsN0,'measured');
%          rxSymbols2 = txSymbols2 + noise;
        rxSymbols2 = awgn(txSymbols2,EsN0,'measured');
         
%         signal_power = mean(abs(txSymbols2).^2);             % 发射信号功率
%         noise_power = mean(abs(rxSymbols2 - txSymbols2).^2); % 差值 = 噪声估计
%         
%         SNR_est_linear = signal_power / noise_power;
%         SNR_est_dB = 10 * log10(SNR_est_linear)
                      
        % ====== 5. 软解调 ======
        softBits = lteSymbolDemodulate(rxSymbols,'QPSK','Soft');
        softBits2 = qamdemod(rxSymbols2, M,'OutputType','approxllr', ...
            'UnitAveragePower',true,'NoiseVariance',noiseVar);
        softBits2 = softBits2*(-1);
        % ====== 6. Turbo译码 ======
%         llrInput = 2 * rxSymbols / noiseVar;
        dataOut = lteTurboDecode(softBits2, maxIter);
        % ====== 7. 错误统计 ======
        numErrs = numErrs + sum(dataOut ~= dataIn);
        numTotal = numTotal + length(dataIn);
    end

    % BER计算
    ber(snrIdx) = numErrs / numTotal;
end
figure
% ====== 绘图 ======
semilogy(EbN0_dB, ber, 'o-', 'LineWidth', 2); grid on;
xlabel('E_b/N_0 (dB)'); ylabel('Bit Error Rate (BER)');
title(sprintf('Turbo编码（LTE标准） - MaxLog-MAP, %d次迭代', maxIter));
legend('Turbo码 (1/3)', 'Location', 'southwest');
```

下图给出QPSK调制下，TURBO链路BER曲线：

![TURBO_BER](/images/2025-07-24-Turbo_LDPC/TURBO_BER.jpg)

#### (b) Turbo码与卷积码误码性能对比仿真

不同 SNR（Eb/N0）条件下，分别统计 Turbo 和卷积编码系统在**软判决**与**硬判决**下的 BER（误码率）。

```matlab
%% TURBO 码和 卷积码对比
clear; close all;
rng default

M = 4;                   % QPSK
k = log2(M);             % Bits per symbol
EbNoVec = (-3:6)';       % Eb/No values (dB)
numSymPerFrame = 2016;   % Bits per frame

rate = 1/3;              % Turbo/Conv 编码率
tbl = 32;                % traceback depth for Viterbi
trellis = poly2trellis(7,[171 133 165]);  % 卷积编码

% 初始化 BER 统计
berTurboSoft = zeros(size(EbNoVec)); 
berTurboHard = zeros(size(EbNoVec));
berConvSoft  = zeros(size(EbNoVec));
berConvHard  = zeros(size(EbNoVec));
h = waitbar(0, 'Running simulation...');
for n = 1:length(EbNoVec)
    snrdB = EbNoVec(n) + 10*log10(k*rate);
    noiseVar = 10^(-snrdB/10);
    
    [errTurboSoft, errTurboHard, errConvSoft, errConvHard, totalBits] = deal(0);
     waitbar(n/length(EbNoVec), h, ...
        sprintf('Simulating: Eb/N0 = %d dB (%.0f%%)', EbNoVec(n), 100*n/length(EbNoVec)));
    while errTurboSoft < 100 && totalBits < 1e6
        % 1. 原始比特
        dataIn = randi([0 1], numSymPerFrame, 1);
        
        %% --- Turbo编码 ---
        dataTurboEnc = lteTurboEncode(dataIn);

        % QAM调制
        txTurbo = qammod(dataTurboEnc,M,'InputType','bit','UnitAveragePower',true);
        rxTurbo = awgn(txTurbo, snrdB, 'measured');
        
        % 硬判决解调
        rxHardTurbo = qamdemod(rxTurbo, M, 'OutputType','bit','UnitAveragePower',true);
        rxHardTurboMapped = rxHardTurbo * -2 + 1;  % 映射为 ±1
        rxHardTurboMapped = -rxHardTurboMapped;    % 翻转符号用于一致性
        
        % 软判决解调
        rxSoftTurbo = qamdemod(rxTurbo, M, 'OutputType','approxllr', ...
            'UnitAveragePower', true, 'NoiseVariance', noiseVar);
        rxSoftTurbo = -rxSoftTurbo;
        
        % Turbo译码
        dataTurboDecSoft = lteTurboDecode(rxSoftTurbo, 5);
        dataTurboDecHard = lteTurboDecode(rxHardTurboMapped, 5);

        errTurboSoft = errTurboSoft + sum(dataIn ~= dataTurboDecSoft);
        errTurboHard = errTurboHard + sum(dataIn ~= dataTurboDecHard);

        %% --- 卷积编码 ---
        dataConvEnc = convenc(dataIn, trellis);

        % QAM调制
        txConv = qammod(dataConvEnc,M,'InputType','bit','UnitAveragePower',true);
        rxConv = awgn(txConv, snrdB, 'measured');
%         rxConv = txConv;
        % 硬判决解调
        rxHard = qamdemod(rxConv,M,'OutputType','bit','UnitAveragePower',true);
        dataConvHard = vitdec(rxHard, trellis, tbl, 'cont', 'hard');
        errConvHard = errConvHard + sum(dataIn(1:end-tbl) ~= dataConvHard(tbl+1:end));

        % 软判决解调
        rxSoft = qamdemod(rxConv,M,'OutputType','approxllr','UnitAveragePower',true,'NoiseVariance',noiseVar);
        dataConvSoft = vitdec(rxSoft, trellis, tbl, 'cont', 'unquant');
        errConvSoft = errConvSoft + sum(dataIn(1:end-tbl) ~= dataConvSoft(tbl+1:end));
        
        totalBits = totalBits + numSymPerFrame;
    end

    % 存储结果
    berTurboSoft(n) = errTurboSoft / totalBits;
    berTurboHard(n) = errTurboHard / totalBits;
    berConvSoft(n)  = errConvSoft  / (totalBits - tbl);
    berConvHard(n)  = errConvHard  / (totalBits - tbl);
    
    fprintf('Eb/N0 = %2d dB: TurboSoft = %.3e, TurboHard = %.3e, ConvSoft = %.3e, ConvHard = %.3e\n', ...
        EbNoVec(n), berTurboSoft(n), berTurboHard(n), berConvSoft(n), berConvHard(n));
end
close(h);
%% 绘图对比
figure; semilogy(EbNoVec, berTurboSoft, '-o', 'LineWidth', 2); hold on;
semilogy(EbNoVec, berTurboHard, '-d', 'LineWidth', 2);
semilogy(EbNoVec, berConvSoft,  '-s', 'LineWidth', 2);
semilogy(EbNoVec, berConvHard,  '-^', 'LineWidth', 2);
semilogy(EbNoVec,berawgn(EbNoVec,'qam',M),'LineWidth', 2);
grid on; xlabel('E_b/N_0 (dB)'); ylabel('BER');
legend('Turbo (Soft)','Turbo (Hard)','Conv (Soft)','Conv (Hard)','Uncoded');
title('BER Comparison: Turbo vs Convolutional (Soft/Hard Decision)');
```

下图给出QPSK调制下的对比曲线：

![TURBO_VS_conv](/images/2025-07-24-Turbo_LDPC/TURBO_VS_conv.jpg)