import {api} from './client.js';
export const batchesApi={list:()=>api('/batches'),create:data=>api('/batches','POST',data),confirm:id=>api('/batches/'+id+'/confirm','POST')};
