import {api,post} from './client.js';
export const datasets={list:()=>api('/datasets'),save:(d,id)=>post('/datasets'+(id?'/'+id:''),d,id?'PUT':'POST')};
export const plans={list:()=>api('/plans'),save:(d,id)=>post('/plans'+(id?'/'+id:''),d,id?'PUT':'POST')};
export const traces={list:()=>api('/traces'),run:d=>post('/traces',d),detail:id=>api('/traces/'+id)};
export const drafts={
 list:datasetId=>api('/drafts'+(datasetId?'?dataset_id='+datasetId:'')),
 detail:id=>api('/drafts/'+id),
 save:(d,id)=>post('/drafts'+(id?'/'+id:''),d,id?'PUT':'POST'),
 trial:(id,plan_id)=>post('/drafts/'+id+'/trial',{plan_id}),
 publish:id=>post('/drafts/'+id+'/publish',{})
};
