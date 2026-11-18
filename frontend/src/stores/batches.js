import {batchesApi} from '../api/batches.js';
export const batchesStore={items:[],async refresh(){this.items=await batchesApi.list();return this.items;}};
