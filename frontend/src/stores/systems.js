import {systemsApi} from '../api/systems.js';
export const systemsStore={items:[],async refresh(){this.items=await systemsApi.list();return this.items;}};
