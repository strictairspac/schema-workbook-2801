import {api} from './client.js';
export const systemsApi={list:()=>api('/systems'),create:data=>api('/systems','POST',data),update:(id,data)=>api('/systems/'+id,'PUT',data)};
