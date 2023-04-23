---
layout: post
title: 收发端测试说明
categories: [自组网, OCAP, 通信]
description: ad hoc 课程路由学习
keywords: 自组网, 通信, 网络层
mermaid: false
sequence: false
flow: false
mathjax: false
mindmap: false
mindmap2: false
---

## 部分代码补充解释

### 定义

#### SINT16 (os_type.h)

```c
typedef signed short int SINT16;
```

SINT16是一个类型别名，表示一个有符号的 16 位短整数（signed short int）。

#### complex_s16_t (algo_cf_api.h)

```c
typedef struct complex_s16_tag
{
    SINT16 s16_re;
    SINT16 s16_im;
} complex_s16_t;
```

在这个结构体中， `s16_re` 表示复数的实部，类型为 `SINT16` （即有符号的 16 位短整数）。 `s16_im` 表示复数的虚部，类型也为 `SINT16` 。结构体类型名为 `complex_s16_t` 。

#### DATA_TCM_WAVEFORM_A_SECTION (WF_XC4210.lsf)

```c
DATA_TCM_WAVEFORM_A_SECTION  at 0x00018000 size 0x00080000
```

这一行描述了`DATA_TCM_WAVEFORM_A_SECTION`的具体内存位置和大小。

`at 0x00018000`：这部分表示该内存段的起始地址是 `0x00018000` ，即十六进制数值 `0x00018000` 。

`size 0x00080000`：这部分表示该内存段的大小为 `0x00080000` 字节，即十六进制数值 `0x00080000` 。

#### DATA_DTCM_UCASE_SECTION  (demo_common.h)

```c
#define DATA_DTCM_UCASE_SECTION   __attribute__((section(".DSECT DATA_TCM_WAVEFORM_A_SECTION")))
```

`DATA_DTCM_UCASE_SECTION` 是一个宏定义，它使用了 GNU C 编译器的 `__attribute__` 语法来指定一个特定的段（section）属性。指示编译器将对象放置在名为 "`.DSECT DATA_TCM_WAVEFORM_A_SECTION`" 的段中。

这样的段属性用于控制程序的内存布局，可将特定的数据放置在特定的内存区域中。

#### DD_SHRAM_X1643 (WF_XC4210.lsf)

```c
DATA_SHRAM3_X1643    at 0x81A00000
```

这一行描述了 `DATA_SHRAM3_X1643` 内存段的起始地址是0x81A00000。

#### DD_SHRAM_X1643 (tx_demo.h)

```c
#define DD_SHRAM_X1643   __attribute__((section(".DSECT DATA_SHRAM3_X1643")))
```

DD_SHRAM_X1643是一个宏定义，用来指示编译器将对象放置在名为 ".DSECT DATA_SHRAM3_X1643" 的段中。

## 发送端

### OFDM调制过程

20MHz 带宽、长数据图发下，频域信号到时域信号所经历的过程如下：

1. 生成频域信号：包括参考信号和数据信号，每个频域符号1200个子载波。

2. 零填充：对每个频域符号执行零填充，将 1200 个子载波数据通过零填充扩展至 2048 个点，以满足 IFFT 的输入要求。

3. IFFT变换：对零填充后的频域信号通过 MRD 加速器进行 IFFT 变换，将其转换为时域符号。

4. 在时域符号前添加循环前缀(CP)，以提供多径抗干扰能力。

5. 添加SS和GP：在时域信号上添加同步前导和保护间隔，以实现接收端的时间和频率同步。

至此得到时域长度为 1ms($30720*T_s$) 的数据突发。

#### 生成频域信号

此处假设通过外部脚本生成。

通过以下方式将1200个频域信号导入XC4210的DTCM中：

```c
DATA_DTCM_UCASE_SECTION complex_s16_t __attribute__((aligned(64))) qpsk_data_1200[] = {
    #include "D:/20220728/OCAP_V3.00.02.P01_HY_20221122/OCAP_V3.00.02.P01_HY_20221122/app/TFWD/XC4210/algo/data/qpsk_data_1200_orign.dat"
};
```

这段代码定义了一个名为 `qpsk_data_1200` 的复数数组，用作暂存频域1200个子载波的数据，其具有特定的内存对齐属性（64字节对齐）和段属性。数组的数据来源于一个外部文件。

#### 零填充

零填充的目的为将子载波数据扩展到 2 的整数次幂点（例如 2048 点），以作为IFFT 的输入。将 1200 个子载波零填充到 2048 点的过程中需要遵循一定的规则，以确保正负频率子载波正确地对应。在 IFFT 输出中，正负频率分量排列在数组的两侧，直流分量位于 0 点数处。因此在这个过程中，将 1200 个子载波数据分为两部分，一部分是负频率子载波，另一部分是正频率子载波。将正频率子载波映射到 2048 点的前半部分，负频率子载波映射到 2048 点的后半部分。零频处包含直流子载波共三个子载波弃用。映射关系见下图：

![图 1](/images/2023-4-23-OCAP_tx_rx_test/IMG_20230423-105516889.png)  

此处单独通过数据搬移实现，后续若频域信号不是从本地读取，完全可以在调制之后直接映射到内存指定位置，直接完成零填充。

```c
size_t size =  sizeof(complex_s16_t); 
memcpy(IFFT_in_data_p + 2, data_1200+600, 600 * size); // 搬移数据
memcpy(IFFT_in_data_p + 1447, data_1200, 600 * size);
```

第一次复制操作将 `data_1200` 中的第600个元素到第1199个元素复制到 `IFFT_in_data_p` 数组的第2个元素到第601个元素；第二次复制操作将 `data_1200` 中的第0个元素到第599个元素复制到 `IFFT_in_data_p` 数组的第1447个元素到第2046个元素。

#### 添加SS和GP

```c
DD_SHRAM_X1643 __attribute__((aligned(64))) complex_s16_t tx_data_prepare[30720] = {
    #include "D:/20220728/OCAP_V3.00.02.P01_HY_20221122/OCAP_V3.00.02.P01_HY_20221122/app/TFWD/XC4210/algo/data/time_domain_ss.dat" 
    };
complex_s16_t * tx_data_prepare_p = tx_data_prepare;
```

上述代码定义了一个名为 `tx_data_prepare` 的 `complex_s16_t` 类型数组，包含30720个元素，用来存放发端一个长突发数据。数组的初始化数据来自于一个外部文件，该文件内部存放长度为656的前导。这个数组具有特定的内存段属性和对齐属性。

为了方便操作，此处定义了一个指针指向`tx_data_prepare`。

#### IFFT变换

IFFT 的实现基于 LC1881 SoC 提供的硬件加速器混合基 DFT（MRD）。 MRD 是XC4210 子系统的 TCE 模块之一，支持正向和反向的复 FFT、 DFT 运算，同时允许用户自定义缩放。输入输出数据宽度均为 16 位。

下图给出 MRD 加速器的工作流程。其中，输入数据必须来自 XC4210 的 DTCM，而输出数据可以选择存储至 DTCM、 SHRAM 或 DDR。数据搬移离不开 XC4210 的 DMA。它与 DTCM 和数据存储控制器共同组成了 XC4210 的数据存储器子系统（Data Memory Subsystem， DMSS）。

![图 2](/images/2023-4-23-OCAP_tx_rx_test/IMG_20230423-110023720.png)  

以下给出 mrd 调用函数的函数原型：

```c
VOID mrd_accelerator(UINT8 *u8p_in_dtcm, UINT8 *u8p_out_base, BOOLEAN b_out_in_dtcm, BOOLEAN fft_flag, SINT32 alpha)
```

| 参数 | 说明 |
|------|------|
|  UINT8 *u8p_in_dtcm    |  一个指向UINT8类型数据的指针，表示输入数据的地址。UINT8是一个无符号8位整数类型 |
| UINT8 *u8p_out_base | 一个指向UINT8类型数据的指针，表示输出数据的基地址
|BOOLEAN b_out_in_dtcm | 一个布尔类型的变量，用于选择输出地址。(1)如果b_out_in_dtcm为TRUE，则输出地址为u8p_out_base + 0x82000000，表示输出到DTCM。(2)如果b_out_in_dtcm为FALSE，则输出地址为u8p_out_base，表示输出到SHRAM或DDR
|BOOLEAN fft_flag | 一个布尔类型的变量，用于判断执行FFT还是IFFT。(1)如果fft_flag为TRUE，则执行IFFT。(2)如果fft_flag为FALSE，则执行FFT。
|SINT32 alpha| 一个SINT32类型的变量，表示频域频移参数。SINT32是一个有符号32位整数类型。alpha的值应在正负1之间。
