---
layout: post
title: DQPSK 和 QPSK 比较
categories: [通信]
description: DQPSK 和 QPSK 比较
keywords: 通信
mermaid: false
sequence: false
flow: false
mathjax: true
mindmap: false
mindmap2: false
---

## 一、基本概念

### 1. QPSK（Quadrature Phase Shift Keying）

QPSK 是一种相位调制技术，通过四种不同的载波相位（如 0°、90°、180°、270°）来表示两个比特的信息。

- 每个符号携带 2 比特（00, 01, 10, 11）。

- 发送的是**绝对相位**，接收端需要**相位参考（或载波同步）**来解调。

### DQPSK（Differential Quadrature Phase Shift Keying）

DQPSK 是 QPSK 的差分版本，不直接调制绝对相位，而是通过当前符号与前一个符号相位差来表示数据。

- 每个符号仍然代表 2 比特。

- 调制的是相位差值，接收端无需恢复载波相位（非相干解调），只需比较前后符号的相位差。

## 二、优缺点分析

| 项目          | QPSK       | DQPSK        |
| ----------- | ---------- | ------------ |
| **解调复杂度**   | 较高（需载波同步）  | 低（无需载波同步）    |
| **误码性能**    | 好（因使用绝对相位） | 稍差（误差可能扩散）   |
| **同步需求**    | 高          | 低            |
| **抗信道频偏性能** | 较差         | 较强           |
| **错误传播**    | 无（单符号错）    | 有（误差可能影响两符号） |

## 三、误码率（BER）对比

在理想AWGN信道中，误码率表达如下：

- QPSK:

$$
P_b=Q\left(\sqrt{2 E_b / N_0}\right)
$$

- DQPSK:

$$
P_b=\frac{1}{2} \exp \left(-\frac{E_b}{N_0}\right)
$$

说明：DQPSK 的误码率比 QPSK 高

## 四、仿真对比

对比 QPSK 与 DQPSK 在 **LDPC** 编码系统下的链路性能

通过 **OFDM 调制**、**AWGN 信道**传输与 **LLR 解调**，统计在不同 Eb/N0 下的 块错误率（BLER）。

```matlab
%% ===============================
%  LDPC 链路随 SNR 变化的蒙特卡洛仿真
%  2025-07-21
%% ===============================
clc; clear; close all;

%% 链路配置
lenCW   = 600;      % 编码后比特长度
lenTB   = 200;       % 信息比特长度
ModOrd  = [2 2];    % 对应 QPSK
maxErr  = 100;      % 每个 SNR 点最少错误帧数（提前停止）
maxFrm  = 15000;      % 每个 SNR 点最大仿真帧数
OFDMsize = 512;SCNum = 300;
% SNR 列表（dB）
EbN0dB_list = -5:1:5;   % 可按需要改

%% 预分配
BLER  = zeros(size(EbN0dB_list));
BLER_dqpsk  = zeros(size(EbN0dB_list));
%% 主循环
for idxSNR = 1:numel(EbN0dB_list)
    EbN0dB = EbN0dB_list(idxSNR);
    % snrdB  = EbN0dB + 10*log10(2);   % 换算为 Es/N0 (QPSK 每符号2比特)
    snrdB = EbN0dB ;
    noiseVar = 10.^(-EbN0dB/10);
    
    errCnt = 0;errCnt2 = 0;
    frmCnt = 0;
    
    while errCnt < maxErr && frmCnt < maxFrm
        frmCnt = frmCnt + 1;
        
        % 1. 生成随机信息比特
        info_bits = randi([0 1], 1, lenTB);
        
        % 2. LDPC 编码
        bits_coded = coding_module(info_bits, 1, lenCW, lenTB, ModOrd, 'LDPC', 0);
        bits_coded_dqpsk = coding_module(info_bits, 1, lenCW-2, lenTB, ModOrd, 'LDPC', 0);
        % bits_coded = bits_coded.';          % 列向量
        
        % 3. QPSK 调制并功率归一化
        % txSym = qammod(bits_coded, 4, 'InputType', 'bit') / sqrt(2);
        txSym =modulation_module(bits_coded, 1, lenCW, ModOrd, 0, 1);
        txSym_dqpsk =modulation_module(bits_coded_dqpsk, 1, lenCW-2, ModOrd, 0, 0);


        TxSignal_beforefft = subcarrier_padding(txSym, OFDMsize, SCNum, 2, 1);
        % OFDM调制
        TxSignal_timedomain = ofdm_modulation(TxSignal_beforefft);
        % 4. AWGN 信道
        TxSignal_timedomain = awgn(TxSignal_timedomain, snrdB, 'measured');
        TxSignal_fredomain = ofdm_demodulation(TxSignal_timedomain);   
        rxSym = subcarrier_extraction(TxSignal_fredomain,OFDMsize,SCNum);

        TxSignal_beforefft2 = subcarrier_padding(txSym_dqpsk, OFDMsize, SCNum, 2, 1);
        % OFDM调制
        TxSignal_timedomain2 = ofdm_modulation(TxSignal_beforefft2);
        TxSignal_timedomain2 = awgn(TxSignal_timedomain2, snrdB, 'measured');
        TxSignal_fredomain2 = ofdm_demodulation(TxSignal_timedomain2);
        rxSym_dqpsk = subcarrier_extraction(TxSignal_fredomain2,OFDMsize,SCNum);
        
        rxSym = rxSym.';rxSym_dqpsk = rxSym_dqpsk.';
        % rxSym = awgn(txSym, snrdB, 'measured');
        % rxSym_dqpsk = awgn(txSym_dqpsk, snrdB, 'measured');
        % rxSym = txSym;     
        % llr = qamdemod(rxSym*sqrt(2), 4, 'OutputType', 'approxllr', ...
        %                'UnitAveragePower', true, 'NoiseVariance', noiseVar);
        % 
        noiseVar_list = noiseVar.*ones(1, 300);
        % 5. 解调 LLR
        llr = softdemodul(rxSym, noiseVar_list, 2, 'Log');
        llr_dqpsk = softdemodul(rxSym_dqpsk, noiseVar_list, 1, 'Log');
        % 6. LDPC 译码
        [crcResult, decoded] = decoding_module(llr, 1, lenCW, lenTB, ModOrd, 'LDPC', 0);
        [crcResult_dqpsk, decoded_dqpsk] = decoding_module(llr_dqpsk, 1, lenCW-2, lenTB, ModOrd, 'LDPC', 0);
        % 7. 误块判断
        if crcResult == 0
            errCnt = errCnt + 1;
        end
        if crcResult_dqpsk == 0
            errCnt2 = errCnt2 + 1;
        end
        % 8. 动态打印
        if mod(frmCnt, 1000) == 0 || (errCnt >= maxErr)
            fprintf('Eb/N0 = %.1f dB, Frames=%d, Errors=%d, BLER=%.3e\n', ...
                    EbN0dB, frmCnt, errCnt, errCnt/frmCnt);
        end
    end
    
    BLER(idxSNR) = errCnt / frmCnt;
    BLER_dqpsk(idxSNR) = errCnt2 / frmCnt;
end

%% 绘图
%% 绘图
codeRate = lenTB / lenCW;  % 计算码率

figure;
semilogy(EbN0dB_list, BLER, 'b-o', 'LineWidth', 1.5);
hold on;
semilogy(EbN0dB_list, BLER_dqpsk, 'r-o', 'LineWidth', 1.5);
grid on;

xlabel('E_b/N_0 (dB)');
ylabel('BLER');
title(sprintf('LDPC 链路 BLER 曲线（码率 = %.3f）', codeRate));
legend('QPSK', 'DQPSK', 'Location', 'southwest');

ylim([1e-4 1]);

```

下图给出1/3码率下性能对比：

![仿真对比](/images\2025-07-23-DQPSK_VS_QPSK\对比_1d3.jpg)