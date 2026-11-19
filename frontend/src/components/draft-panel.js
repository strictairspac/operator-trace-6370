import {store} from '../stores/business.js';
import {drafts} from '../api/business.js';
import {esc,json} from '../utils/html.js';
import {table} from './common/table.js';
import {DRAFT_STATUSES,PUBLISH_REASONS} from '../constants/enums.js';
import {feedback} from './common/feedback.js';

const emptyChanges={inserts:[],updates:[],deletes:[]};
const viewer=()=>store.user?.role==='viewer';

export function draftPanel(){
 return `<section class="draft-board">
 <h2>采样草稿工作台 <em>${store.drafts.length}</em></h2>
 <p>助教把采样的增删改先存成草稿，不触碰正式数据；选一份计划试跑，通过后整批发布。每行采样有稳定 row_id，同值采样也能单独修改。</p>
 <div class="split">
 <form id="draft-form">
 <input name="id" type="hidden">
 <label>所属数据集<select name="dataset_id">${store.datasets.map(d=>`<option value="${d.id}">${esc(d.name)} <small>v${d.version}</small></option>`).join('')}</select></label>
 <label>草稿名称<input name="name" required placeholder="日班高温追加-草稿"></label>
 <label>变更 JSON（inserts / updates / deletes）<textarea name="changes" class="code-input" rows="12" required>${json(emptyChanges)}</textarea></label>
 <div class="duo">
  <input id="draft-insert-sensor" type="number" min="1" placeholder="sensor_id">
  <input id="draft-insert-value" type="number" step="any" placeholder="value">
 </div>
 <input id="draft-insert-at" placeholder="recorded_at，如 2026-11-17T10:00:00">
 <button type="button" class="quiet" id="draft-add-insert">追加一条插入（自动 cid）</button>
 <small>更新/删除请在下方采样行浏览器点「改 / 删」，按 row_id 加入变更；发布按 cid 去重，失败重试不会重复追加。</small>
 <button type="submit">保存草稿</button>
 <button type="button" data-reset="draft-form" class="quiet">清空</button>
 </form>
 <div>
 ${table(['草稿','状态','试跑 / 发布','动作'],store.drafts.map(d=>[
  `<b>${esc(d.name)}</b><small>${esc(store.datasets.find(x=>x.id===d.dataset_id)?.name||('数据集#'+d.dataset_id))} · ${d.changes.inserts.length}增 ${d.changes.updates.length}改 ${d.changes.deletes.length}删</small>`,
  `<span class="status ${d.status==='published'?'completed':'running'}">${DRAFT_STATUSES[d.status]||d.status}</span>`,
  draftTrialCell(d),
  draftActions(d)
 ]))}
 <div id="draft-detail"></div>
 </div>
 </div>
 <div id="draft-browser"></div>
 </section>`;
}

function draftTrialCell(d){
 if(d.status==='published')return `<small>${esc(d.publish?.message||'已发布')}</small><code class="checksum">${esc((d.publish?.checksum||'').slice(0,18))}…</code>`;
 const plans=store.plans.filter(p=>p.dataset_id===d.dataset_id);
 const fail=d.publish&&d.publish.reason!=='ok'?`<div class="feedback error" style="margin:8px 0 0">${esc(PUBLISH_REASONS[d.publish.reason]||d.publish.reason)}：${esc(d.publish.message)}</div>`:'';
 return `<select data-trial-plan="${d.id}">${plans.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('')}</select>
 <button class="quiet" data-draft-trial="${d.id}" ${viewer()?'disabled':''}>试跑</button>${fail}`;
}

function draftActions(d){
 const pub=d.status==='published'?'':`<button class="quiet" data-draft-publish="${d.id}" ${viewer()||d.status!=='trial_completed'?'disabled title="先完成试跑再发布"':''}>发布</button>`;
 return `<button class="quiet" data-draft-view="${d.id}">详情/行</button>${pub}`;
}

export function bindDrafts(refreshAndRender){
 const form=document.getElementById('draft-form');
 document.getElementById('draft-add-insert')?.addEventListener('click',()=>{
  const sensor=Number(document.getElementById('draft-insert-sensor').value);
  const value=Number(document.getElementById('draft-insert-value').value);
  const at=document.getElementById('draft-insert-at').value.trim();
  if(!sensor||!Number.isFinite(value)||!at){feedback('请填全 sensor_id / value / recorded_at',true);return;}
  const ch=readChanges();
  ch.inserts.push({cid:'c-'+Date.now()+'-'+Math.floor(Math.random()*1e4),payload:{sensor_id:sensor,value:value,recorded_at:at}});
  writeChanges(ch);feedback('已加入插入变更，保存草稿后生效。');
 });
 form?.addEventListener('submit',async e=>{
  e.preventDefault();
  const fd=new FormData(form);
  const id=fd.get('id');
  const body={name:fd.get('name'),dataset_id:Number(fd.get('dataset_id')),changes:readChanges()};
  const btn=form.querySelector('[type=submit]');btn.disabled=true;
  try{
   const saved=await drafts.save(body,id||undefined);
   feedback(id?'草稿已更新，原试跑结果已失效，请重新试跑。':'草稿已保存，可以选择计划试跑。');
   form.reset();form.elements.id.value='';writeChanges(emptyChanges);
   await refreshAndRender();
   await viewDraft(saved.id);
  }catch(err){feedback(err.message,true);}finally{btn.disabled=false;}
 });
 document.querySelectorAll('[data-draft-trial]').forEach(b=>b.onclick=async()=>{
  const id=b.dataset.draftTrial;
  const plan_id=Number(document.querySelector(`[data-trial-plan="${id}"]`).value);
  b.disabled=true;
  try{await drafts.trial(id,plan_id);feedback('试跑完成，请核对结果后发布。');await refreshAndRender();await viewDraft(id);}
  catch(err){feedback(err.message,true);}finally{b.disabled=false;}
 });
 document.querySelectorAll('[data-draft-publish]').forEach(b=>b.onclick=async()=>{
  const id=b.dataset.draftPublish;b.disabled=true;
  try{await drafts.publish(id);feedback('整批发布成功，正式数据已切换到新版本。');await refreshAndRender();await viewDraft(id);}
  catch(err){feedback(err.message,true);await refreshAndRender();await viewDraft(id);}
  finally{b.disabled=false;}
 });
 document.querySelectorAll('[data-draft-view]').forEach(b=>b.onclick=()=>viewDraft(b.dataset.draftView));
 document.querySelectorAll('[data-draft-browse]').forEach(b=>b.onclick=()=>browseRows(Number(b.dataset.draftBrowse)));
 document.querySelectorAll('[data-draft-row]').forEach(b=>b.onclick=()=>{
  const [op,dsId,rid]=b.dataset.draftRow.split(':');
  patchRowChange(op,Number(dsId),Number(rid));
 });
}

function readChanges(){
 try{return JSON.parse(document.getElementById('draft-form').elements.changes.value);}
 catch{feedback('变更 JSON 格式不正确',true);throw new Error('bad changes json');}
}
function writeChanges(ch){document.getElementById('draft-form').elements.changes.value=JSON.stringify(ch,null,2);}

function patchRowChange(op,datasetId,rowId){
 const form=document.getElementById('draft-form');
 if(Number(form.elements.dataset_id.value)!==datasetId){form.elements.dataset_id.value=String(datasetId);}
 const ch=readChanges();
 const ds=store.datasets.find(d=>d.id===datasetId);
 const row=ds.readings.find(r=>r.row_id===rowId);
 if(!row){feedback('该行已不存在',true);return;}
 if(op==='delete'){
  if(!ch.deletes.some(x=>x.row_id===rowId))ch.deletes.push({row_id:rowId});
  ch.updates=ch.updates.filter(x=>x.row_id!==rowId);
 }else{
  const value=prompt('修改 value（sensor_id/recorded_at 可在 JSON 中继续改）',String(row.value));
  if(value===null)return;
  const payload={sensor_id:row.sensor_id,value:Number(value),recorded_at:row.recorded_at};
  ch.updates=ch.updates.filter(x=>x.row_id!==rowId);
  ch.updates.push({row_id:rowId,payload});
  ch.deletes=ch.deletes.filter(x=>x.row_id!==rowId);
 }
 writeChanges(ch);feedback(`row_id ${rowId} 的${op==='delete'?'删除':'更新'}已加入变更。`);
}

async function viewDraft(id){
 let d;
 try{d=await drafts.detail(id);}catch(err){feedback(err.message,true);return;}
 const box=document.getElementById('draft-detail');
 if(!box)return;
 const t=d.trial;
 box.innerHTML=`<h3>草稿详情 · ${esc(d.name)}</h3>
 ${d.publish?`<div class="feedback ${d.publish.reason==='ok'?'':'error'}">${esc(PUBLISH_REASONS[d.publish.reason]||d.publish.reason)} — ${esc(d.publish.message)}</div>`:''}
 ${t?`<div class="metrics"><div><small>试跑计划</small><strong>${esc(t.plan.name)}</strong></div><div><small>合并后行数</small><strong>${t.merged_rows}<em>rows</em></strong></div><div><small>试跑输出</small><strong>${t.result.output_rows}<em>行</em></strong></div></div>
 <code class="checksum">${esc(t.result.checksum)}</code>
 <details ${d.publish?.reason!=='ok'?'open':''}><summary>试跑逐算子结果</summary><pre>${json(t.result.operators.map(o=>({op:o.op,input_rows:o.input_rows,output_rows:o.output_rows,checksum:o.checksum})))}</pre></details>`:'<p class="muted">尚未试跑。选择计划后点「试跑」。</p>'}
 ${d.publish?.reason==='row_conflict'?`<details open><summary>撞改行明细（${d.publish.conflicts.length}）</summary><pre>${json(d.publish.conflicts)}</pre></details>`:''}
 ${d.publish?.reason==='result_drift'?`<details open><summary>试跑 vs 重算 checksum</summary><pre>${json({trial:d.publish.trial_checksum,replay:d.publish.replay_checksum,trial_output_rows:d.publish.trial_output_rows,replay_output_rows:d.publish.replay_output_rows,live_version:d.publish.live_version,trial_base_version:d.publish.trial_base_version})}</pre></details>`:''}
 ${d.preview?`<details><summary>合并后采样预览（${d.preview.merged_rows} 行，含 row_id）</summary><pre>${json(d.preview.merged_readings)}</pre></details>
 <button class="quiet" data-draft-browse="${d.dataset_id}">打开采样行浏览器（增改删助手）</button>`:''}`;
 document.querySelectorAll('[data-draft-browse]').forEach(b=>b.onclick=()=>browseRows(Number(b.dataset.draftBrowse)));
}

export function browseRows(datasetId){
 const ds=store.datasets.find(d=>d.id===datasetId);
 const box=document.getElementById('draft-browser');
 if(!box)return;
 box.innerHTML=`<h3>采样行浏览器 · ${esc(ds.name)} <small>v${ds.version} / ${ds.readings.length} 行</small></h3>
 <div class=table-wrap><table><thead><tr><th>row_id</th><th>sensor_id</th><th>value</th><th>recorded_at</th><th>加入草稿</th></tr></thead><tbody>
 ${ds.readings.map(r=>`<tr><td><em>${r.row_id}</em></td><td>${esc(r.sensor_id)}</td><td>${esc(r.value)}</td><td><small>${esc(r.recorded_at)}</small></td>
 <td><button class="quiet" data-draft-row="update:${ds.id}:${r.row_id}" ${viewer()?'disabled':''}>改</button>
 <button class="quiet" data-draft-row="delete:${ds.id}:${r.row_id}" ${viewer()?'disabled':''}>删</button></td></tr>`).join('')}
 </tbody></table></div>`;
 document.querySelectorAll('[data-draft-row]').forEach(b=>b.onclick=()=>{
  const [op,id,rid]=b.dataset.draftRow.split(':');
  patchRowChange(op,Number(id),Number(rid));
 });
 box.scrollIntoView({behavior:'smooth',block:'center'});
}
