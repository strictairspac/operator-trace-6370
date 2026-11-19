# Schema v2

## datasets
- 新增 `version INTEGER NOT NULL DEFAULT 1`：每次整表保存或草稿整批发布递增；trace 快照写入 `dataset_version`，剖面可区分完整旧版/新版。
- `readings` 每行新增持久化稳定 `row_id`（正整数，数据集内唯一）。旧数据由应用在首次保存时补齐；同值采样凭 row_id 独立增删改。row_id 不进入 Python 算子执行视图与 checksum；草稿插入行的 `cid` 同为草稿期去重令牌，发布落库与执行视图均会剥离。

## dataset_drafts（新表）
| 列 | 说明 |
|---|---|
| id | 主键 |
| name | 草稿名称 |
| dataset_id | 所属数据集 FK |
| changes | `{inserts:[{cid,payload}], updates:[{row_id,payload}], deletes:[{row_id}]}` |
| base_readings | 建草稿时正式 readings 的基线快照（含 row_id），用于撞改检测 |
| status | `open` / `trial_completed` / `published` |
| trial | 试跑计划快照、基线版本、合并行数与完整执行结果（含 checksum） |
| publish | 最近一次发布结论：`ok` / `row_conflict`（撞改行明细）/ `result_drift`（试跑与重算 checksum 对比） |
| created_by / created_at / updated_at | 审计字段 |

发布在单事务内完成（`SELECT ... FOR UPDATE` 锁定数据集行）：撞改或漂移时不写入任何变更并返回 409；成功时整批替换 readings 并递增 version。已发布草稿重复调用直接返回，插入按 cid 去重，重试不会重复追加采样。
