/** @typedef {{id:number,name:string,sensors:object[],readings:object[],version:number}} Dataset */
/** @typedef {{id:number,name:string,dataset_id:number,steps:object[]}} Plan */
/** @typedef {{id:number,name:string,status:'queued'|'running'|'completed'|'failed',result:object|null,snapshot:object}} Trace */
/** @typedef {{cid?:string,row_id?:number,payload?:object}} DraftChange */
/** @typedef {{id:number,name:string,dataset_id:number,changes:{inserts:DraftChange[],updates:DraftChange[],deletes:DraftChange[]},status:'open'|'trial_completed'|'published',trial:object|null,publish:object|null,preview:object|null}} DatasetDraft */
export {};
