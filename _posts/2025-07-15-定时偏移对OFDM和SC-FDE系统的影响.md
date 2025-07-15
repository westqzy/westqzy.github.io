---
layout: post
title: 定时偏移对OFDM和SC-FDE系统的影响
categories: [OFDM, SC-FDE, 通信]
description: 定时偏移对OFDM和SC-FDE系统的影响
keywords: OFDM, SC-FDE, 通信
mermaid: false
sequence: false
flow: false
mathjax: True
mindmap: false
mindmap2: false
---


## 背景简介

在 OFDM 和 SC-FDE 系统中，接收端需准确确定 FFT 窗口的起始位置。

在 OFDM 与 SC-FDE 系统中，为避免符号间干扰（ISI），发送端会在每个符号前插入长度为$$L_{CP}$$的循环前缀。

在理想情况下，接收端应准确地在有效符号起始处开始 FFT 处理；但现实中由于定时误差，FFT 窗口可能提前取样至 CP 区域。

此时：

- **只要 FFT 窗口仍在 CP 范围内，系统不会产生 ISI；**

- 会造成子载波（或频域符号）出现线性相位旋转；

- 此相位旋转可通过频域乘以线性相位反向补偿。


本笔记旨在研究： 

当接收端在 CP 范围内提前取样（timing advance）时，**OFDM 与 SC-FDE 系统的性能是否受影响？如何补偿这类相位失真？**

## 理论分析

### ✅ OFDM 系统

- 若采样点在 CP 内偏移 $$ n_0 $$，FFT 输入变为$$  x[n - n_0] $$

- 在频域造成线性相位旋转：
  $$
  X'[k] = X[k] \cdot e^{-j 2\pi kn_0/N}
  $$

- 可通过频域补偿因子：
  $$
  H[k] = e^{+j 2\pi kn_0/N}
  $$
  来逆转偏移。

### ✅ SC-FDE 系统

- 同样受到线性相位旋转影响；

- **频域均衡器必须补偿此相位失真**，否则会在判决前造成畸变；

- 相关理论与 OFDM 系统类似

---

## 仿真流程

### OFDM 收发流程

**发送流程**：

1. QPSK 调制

2. IFFT 生成时域 OFDM 符号

3. 添加循环前缀

**接收流程**：

1. 假设采样窗口提前 $$n_0$$ 个采样点

2. 截取有效窗口数据并去CP

3. FFT 生成频域信号

4. 构造等效信道冲激响应并求信道频域响应 

5. 频域均衡

6. 解调

### SC-FDE 收发流程

**发送流程**：

1. QPSK 调制

2. 添加循环前缀

**接收流程**：

1. 假设采样窗口提前 $$n_0$$ 个采样点

2. 截取有效窗口数据并去CP

3. FFT 生成频域信号

4. 构造等效信道冲激响应并求信道频域响应 

5. 频域均衡

6. IFFT 生成时域信号

7. 解调

## 仿真参数

| 参数        | 数值       |
|-------------|------------|
| 子载波数    | 64         |
| CP长度      | 16         |
| 调制方式    | QPSK       |
| 符号数      | 1000       |
| 信噪比      | 20 dB      |
| 偏移范围    | 0 ～ 15（在CP内） |

---

## 仿真代码

```matlab
clc; clear; close all;

%% OFDM参数
N = 64;               % 子载波数
CP = 16;              % 循环前缀长度
M = 4;                % QPSK调制
numSymbols = 1000;    % OFDM符号数
SNR_dB = 20;          % 固定信噪比

%% 生成发送数据
data = randi([0 M-1], N * numSymbols, 1);
modData = pskmod(data, M, pi/M);    % QPSK调制
txSymbols = reshape(modData, N, []);
ifftData = ifft(txSymbols, N);

% 添加循环前缀
ofdm_with_cp = [ifftData(end-CP+1:end,:); ifftData];
txSignal = ofdm_with_cp(:);   % 串行化

% SC-FDE直接時域發送
SC_with_cp =  [txSymbols(end-CP+1:end,:); txSymbols];
txSignal_sc = SC_with_cp(:);

%% 模拟不同定时提前（取样点在CP范围内）
timing_offsets = 0:CP-1;
ber = zeros(size(timing_offsets));
ber_sc = zeros(size(timing_offsets));

for k = 1:length(timing_offsets)
    offset = timing_offsets(k);

    % 添加AWGN信道
    rxSignal = awgn(txSignal, SNR_dB, 'measured');
    % rxSignal = txSignal;
    rxSignal_sc = txSignal_sc;
    % 模拟定时提前
    rxSignal = reshape(rxSignal, N+CP, []);
    rxSignal_sc = reshape(rxSignal_sc, N+CP, []);
    rxShifted = rxSignal(1+CP-offset:CP-offset+N,:);
    rxShifted_sc = rxSignal_sc(1+CP-offset:CP-offset+N,:);


    % 信道頻率响应
    h = zeros(N,1);
    h(1+offset) = 1;
    H2 = fft(h);

    % OFDM去除CP并FFT
    rx_no_cp = rxShifted;
    H3 = fft(rx_no_cp(:,1))./  txSymbols(:,1);
    h3 = ifft(H3);
    %H = exp(-1j * 2 * pi / N * (offset) * ((1:N)-1));   % 频率响应
    rxFFT = fft(rx_no_cp, N);
    rxFFT = rxFFT./H2;
    % FDE
    rx_no_cp_sc = rxShifted_sc;
    rxIFFT_sc = fft(rx_no_cp_sc, N);
    rxIFFT_sc = rxIFFT_sc./H2;
    rxFFT_sc = ifft(rxIFFT_sc, N);
    % 解调
    rxData = pskdemod(rxFFT(:), M, pi/M);
    data_tx = data(1:length(rxData));
    
    rxData_sc = pskdemod(rxFFT_sc(:), M, pi/M);
    % 误码率
    ber(k) = sum(rxData ~= data_tx) / length(data_tx);
    ber_sc(k) = sum(rxData_sc ~= data_tx) / length(data_tx);
end

%% 绘图
figure;
plot(timing_offsets, ber, '-o');
xlabel('定时提前采样点数（在CP内）');
ylabel('BER');
title('定时提前对OFDM系统性能的影响（SNR=20dB）');
grid on;

N = 64;
n0 = 10;  % 平移的点数

h = zeros(1,N);
h(n0+1) = 0;   % 注意 MATLAB 下标从1开始

H = fft(h, N);
f = (0:N-1)/N;

figure;
subplot(2,1,1);
plot(f, abs(H), 'o-');
title('频率响应幅度');
ylabel('|H(f)|'); grid on;

subplot(2,1,2);
plot(f, angle(H), 'o-');
title('频率响应相位');
ylabel('∠H(f)'); xlabel('归一化频率'); grid on;
```