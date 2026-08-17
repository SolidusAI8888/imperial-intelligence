# 帝王智库 Imperial Intelligence

一个以权威历史资料为事实底座、从历史经验中提炼可迁移洞察，并由最相关历史人物以其完整人生经验参与现代问题咨询的 AI 项目。

## 产品原则

- 历史事实优先：历史结论必须可追溯到 Source Corpus。
- 经验优先：先讲相关人生经历，再谈洞察、借鉴与建议。
- 人物是经验表达主体，不是知识库本身。
- 默认采用人物完整生命周期视角，不把后见之明倒灌为事件当时认知。
- 最终决定权属于提问者；系统提供参考与启发，不替用户做决定。

## 当前架构

```text
Historical Source Corpus
        ↓
Knowledge Layer
        ↓
Historical Experience Units (HEU)
        ↓
Matching
        ↓
Persona Runtime
        ↓
Master Consultation Report
        ↓
Content Runtime
```

Architecture V1 已冻结，相关运行时约束位于 `runtime/contracts/`。

## Historical Source Corpus

项目维护独立于人物的史料全文底座。Phase 1 按朝代顺序建设：

1. 汉
2. 唐
3. 宋

当前登记的一级史料包括：

- 汉：《史记》《汉书》《后汉书》
- 唐：《旧唐书》《新唐书》《资治通鉴·唐纪》《贞观政要》
- 宋：《宋史》

史料正文、版本信息、来源、revision、checksum 与 provenance 位于 `history/source_corpus/`；派生解释、HEU 和咨询内容不得写入原始史料层。

### Source Corpus 权利说明

古代作品本身属于公有领域；当前数字底本及编辑性贡献的具体来源和再利用条件以每一卷对应的 provenance 记录为准。现阶段主要数字见证来自中文维基文库，相关编辑贡献按其适用许可保留来源与版本追溯信息。

**不要把仓库根目录的项目代码与 Source Corpus 视为同一种许可对象。** 当前仓库尚未授予统一的项目代码开源许可证；在正式选择项目许可证前，代码默认保留权利。第三方史料和数字文本遵循各自 provenance 中记录的权利状态。

## 历史数据工具

本地归档：

```bash
python history/tools/ingest_wikisource_phase1.py
```

单独处理一个来源：

```bash
python history/tools/ingest_wikisource_phase1.py --source-id CN-HAN-0001
```

完整性与正文纯净度审计：

```bash
python history/tools/audit_phase1_corpus.py
```

GitHub Actions 用于验证、测试和审计；大规模史料归档优先在本地执行。

## Backend 快速启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开：

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## 安全提醒

仓库公开前及每次提交前，不得提交 `.env`、API Key、访问令牌、私钥、Cookie、数据库密码或个人敏感信息。`.gitignore` 已覆盖常见本地密钥和环境文件，但这不能替代对 Git 历史的人工/自动检查。
