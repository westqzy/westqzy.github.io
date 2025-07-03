---
layout: post
title: 核间通信与线程通信区别
categories: [自组网, OCAP, 通信]
description: 核间通信与线程通信学习笔记
keywords: 自组网, 通信, OCAP
mermaid: false
sequence: false
flow: false
mathjax: false
mindmap: false
mindmap2: false
---

## 线程通信

首先假设一个线程 1 给 线程 2 发送消息的场景

### 发送方配置

1. 消息队列的创建

    **函数原型**

    ```c
    UINT16 osa_msg_queue_create(IN CONST_UINT16 u16_mb_size)
    // 其中：
    // u16_mb_size:申请的 mb 块大小，单位 byte
    // 若成功则返回消息队列 ID 号，否则返回 0xffff
    ```

    **例如**

    ```c
    demo_queue_id = osa_msg_queue_create(10);
    ```

2. 消息的创建
    **函数原型**

    ```c
    osa_msg_t *osa_msg_create(IN CONST_UINT16 u16_pool_id, IN CONST_UINT16 u16_msg_len)
    // 其中:
    // u16_pool_id：消息使用的内存池 ID 
    // u16_msg_len：申请消息的长度(BYTE)
    // 函数返回分配消息的首地址
    ```

    **例如**

    ```c
    test_msg_ptr = OSA_MSG_CREATE(DEMO_MSG_POOL_ID, 2);
    ```

3. 发送消息

   **函数原型**

   ```c
    OSA_STATUS osa_msg_send(IN CONST_UINT16 u16_queue_id,
            IN osa_msg_t * stp_msg,
            IN CONST_UINT32 u32_timeout)
    // 其中：
    // u16_queue_id：目标消息队列 ID 编号
    // stp_msg: 消息的首地址
    // u32_timeout:等待选项，具体可查阅用户接口手册
    // 函数返回 osa 状态
   ```

    **例如**

    ```c
    OSA_MSG_SEND(demo_queue_id, test_msg_ptr, OSA_WAIT_FOREVER);
    ```

### 接收方配置

1. 接收消息

    **函数原型**

    ```c
    osa_msg_t *osa_msg_receive(IN CONST_UINT16 u16_queue_id,
            IN CONST osa_prim_id_t *stp_prim_id,
            IN CONST_UINT32 u32_timeout)
    // 其中：
    // u16_queue_id: 目标消息队列 ID 编号
    // stp_prim_id: 用于接收指定 ID 的消息, 具体可查阅用户接口手册
    // u32_timeout: 等待选项
    // 若运行成功，返回消息地址。否则，返回空指针
    ```

    **例如**

    ```c
    osa_prim_id_t prim_id[2] = {1, OSA_MSG_ANY_ID};
    // 上面一行意味着：接收一个消息，消息 ID 为 OSA_MSG_ANY_ID
    fsm_msg_ptr = osa_msg_receive(demo_queue_id, prim_id, OSA_WAIT_FOREVER);
    // tips: demo_queue_id 为全局变量, 发送和接收方都知道的
    if (NULL_PTR != fsm_msg_ptr){
        // your code
    }
    ```

2. 释放消息

    **函数原型**

    ```c
    VOID osa_msg_release(IN osa_msg_t *stp_msg)
    // 其中
    // stp_msg：消息的首地址
    ```

    **例如**

    ```c
    OSA_MSG_RELEASE(fsm_msg_ptr);
    ```

## 核间通信

依赖函数主要如下

### 发送方发送数据

1. 打开核间通信服务

    **函数原型**

    ```c
    SVR_HANDLE svr_open(CHAR_PTR charp_svr_name,
            UINT32_PTR u32p_status,
            CONST_UINT32 u32_op_flag)
    // 其中 
    // charp_svr_name:打开核间通信服务，名称"BRIDGE"或"HSC", 分别为标准和高速核间通信服务
    // u32p_status: 输出打开服务操作的结果
    // u32_op_flag: 默认为0，本服务下该参数无效
    // 函数返回服务句柄
    ```

    **例如**

    ```c
    g_demo_svr_handler[u32_i] = svr_open("BRIDGE", &s32_status, u32_op_flag);
    //上述实现了开启一个标准核间通信服务，返回值可根据核号的不同而存入数组的不同位置，以此实现发给不同的核
    ```

2. 控制服务类型及相关参数

    **函数原型**

    ```c
    OSA_STATUS svr_control (SVR_HANDLE svr_handle,
            UINT32 cmd,
            VOID * parm);
    // 其中
    // svr_handle:服务句柄
    // cmd: 服务控制命令, 详见用户接口文档
    // parm: 详见用户接口文档
    // 函数返回服务控制状态，返回成功或异常原因
    ```

    此函数没搞懂

3. 通过服务写入核间通信数据

    **函数原型**

    ```c
    OSA_STATUS svr_write (SVR_HANDLE svr_handle, // 服务句柄
            CHAR * user_buf, // 发送数据buffer地址
            UINT32 count, // 期望发送字节数
            UINT32 * pReadCount, // 输出参数，实际发送字节数
            UINT32 op_flag); // 等待超时时间，单位ms
    // 函数返回服务读状态：成功或者异常原因
    ```

    **注**：上述为 bridge 通道各参数说明，高速通道略有不同，详情请查阅用户接口手册

    **例子**

    ```c
    s32_svr_result = svr_write(g_demo_svr_handler[0], 
            (CHAR_PTR)stp_msg, 
            u32_data_len, 
            &u32_write_size,
            OSA_WAIT_FOREVER);
    // 其中发送数据地址通过 CHAR_PTR 将消息地址进行强制转换
    ```

### 接收方接收数据

1. 通过服务读取核间通信数据

   **函数原型**

    ```c
    OSA_STATUS svr_read (SVR_HANDLE svr_handle, // 服务句柄
            CHAR * user_buf, // 接收数据buffer指针
            UINT32 count, // 期望接收的字节数
            UINT32 * pReadCount, // 实际接收的字节数
            UINT32 op_flag); // 等待超时时间，单位ms
    // 函数返回服务读状态：成功或者异常原因
    ```

    **注**：上述为 bridge 通道各参数说明，高速通道略有不同，详情请查阅用户接口shouce

    **例子**

    ```c
    u32_svr_handle = g_demo_svr_handler[0];
    // 服务句柄可以根据不同的核做相对应的选取
    u32_svr_result = svr_read(u32_svr_handle, 
            chap_data_buf, 
            s32_loop, 
            &u32_read_size, 
            OSA_WAIT_FOREVER);
    ```

2. 关闭指定服务

    **函数原型**

    ```c
    OSA_STATUS svr_close (SVR_HANDLE svr_handle);
    // 其中
    // svr_handle: 要关闭的服务句柄
    // 函数返回服务关闭状态：成功或者异常原因
    ```
