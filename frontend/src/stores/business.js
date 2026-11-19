import {datasets,plans,traces,drafts} from '../api/business.js';
export const store={datasets:[],plans:[],traces:[],drafts:[],user:null};
export async function refresh(){[store.datasets,store.plans,store.traces,store.drafts]=await Promise.all([datasets.list(),plans.list(),traces.list(),drafts.list()]);}
