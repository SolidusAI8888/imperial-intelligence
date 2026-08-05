# 帝王智库 Imperial Intelligence

一个基于历史证据、人格模型与决策规则构建的中国历代帝王智能顾问平台。

## 当前阶段

V0.1 项目骨架，目标：

- 建立可复制的帝王人格数据包标准
- 以唐太宗（贞观十五年）作为第一个完整样本
- 提供统一 API，供未来手机网页、PWA 和数字人客户端调用
- 保留证据、争议、人格参数、决策规则、语言与动作模型

## 快速启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开：

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

## 第一阶段接口

- `GET /health`
- `GET /emperors`
- `GET /emperors/{emperor_id}`
- `GET /emperors/{emperor_id}/persona`
- `POST /emperors/{emperor_id}/consult`

`consult` 当前返回结构化占位结果，后续接入：
证据检索 → 人格推理 → 现代风险校正 → 数字人表现指令。
