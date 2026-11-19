export const ROLES={admin:'管理员',operator:'操作员',viewer:'观察员'};
export const STATUSES={queued:'等待执行',running:'执行中',completed:'已完成',failed:'执行失败'};
export const DRAFT_STATUSES={open:'草稿待试跑',trial_completed:'已试跑待发布',published:'已整批发布'};
export const PUBLISH_REASONS={ok:'整批发布成功',row_conflict:'撞改同一行',result_drift:'合并后结果漂移'};
export const OPERATORS=['scan','filter','hash_join','group'];
